"""Synthetic inputs and an independent integer oracle; no graphics imports."""
import csv
import hashlib
import io
import json
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PINS = {
    'baseline.dxil': (9796, '97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208'),
    'synthetic-VB.bin': (192, '6eafd2b9be2b1e05f561354f412f39767ac12e0f2c52c2828ab8d3aa8755062e'),
    'synthetic-CB.bin': (24576, '042c7614dc2c0de57fbf95dcc35eebf509cc2e5603d701d692f78de7e788f827'),
    'oracle.bin': (448, '9db85bb2a574f2a71b3a9e0da815f0f71d80cabfa6047d83c87017d6d787f92f'),
    'known-bad.bin': (448, '5f1babdb87258733bb7dfbfc4d14eb223be0b9bd0367600c84dc61f3553bc5cf'),
}
HLSL_SHA = '0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb'


# All cases use the same synthetic inputs, oracle and graphics interface.
CASES = {
    'baseline': {
        'source': 'source/baseline.hlsl',
        'source_sha256': '0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb',
        'shader': 'data/baseline.dxil',
        'bytes': 9796,
        'sha256': '97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208',
    },
    'scalar-amended': {
        'source': 'source/baseline.hlsl',
        'source_sha256': '0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb',
        'shader': 'data/scalar-amended.dxil',
        'bytes': 9888,
        'sha256': 'c01d780f23507751170192927f15cb6359c23c951fa0b523a46dd04a42ac20b5',
    },
    'out-amended': {
        'source': 'source/out-result.hlsl',
        'source_sha256': '9a5eb0daae3aa6149d6f728bbfb2f4176a7c29158ccab9a11dfe29d289a2d5ae',
        'shader': 'data/out-amended.dxil',
        'bytes': 12432,
        'sha256': 'f56f47c68fe29980d76b961e0e86a4ccf3e469fd21fe0b877be6536123cdab00',
    },
    'array-stock': {'source': 'source/array-inout.hlsl', 'source_sha256': '6723b7232c85b761d49bfbaa9e6d6c269a0df82ea74470544bc721c15f9e040f', 'shader': 'data/array-stock.dxil', 'bytes': 15724, 'sha256': '1fbed79006488999391766c4471ad9dfe7ca2b38f4b0e813f2619d5443e80572'},
}


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def put(path, data):
    """Exclusive, flushed evidence. Never overwrite a previous attempt."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    with Path(path).open('xb') as f:
        need(f.write(data) == len(data), 'short output write')
        f.flush()
        os.fsync(f.fileno())


def put_json(path, value):
    put(path, json.dumps(value, indent=2, allow_nan=False) + '\n')


def words(data):
    need(len(data) % 4 == 0, 'word alignment')
    return struct.unpack('<' + 'I' * (len(data) // 4), data)


def integer(bits):
    exponent = (bits >> 23) & 255
    need(bits >> 31 == 0 and 127 <= exponent <= 150, 'positive integral binary32')
    mantissa, divisor = (bits & 0x7fffff) | 0x800000, 1 << (150 - exponent)
    need(mantissa % divisor == 0, 'integral mantissa')
    return mantissa // divisor


def encode(value):
    need(0 < value < 1 << 24, 'exact positive integer range')
    exponent = value.bit_length() - 1
    return ((exponent + 127) << 23) | ((value - (1 << exponent)) << (23 - exponent))


def oracle(vb, cb):
    need(len(vb) == 192 and len(cb) == 24576, 'input shape')
    palette = [integer(w) for w in words(cb)]
    need(palette == list(range(1, 6145)), 'literal palette')
    result, maximum = [], 0
    for vertex in range(4):
        v = words(vb[vertex * 48:(vertex + 1) * 48])
        position, weights, indices = list(map(integer, v[:4])), list(map(integer, v[4:8])), v[8:]
        need(all(p <= 16 for p in position), 'position bound')
        need(weights == [1, 2, 3, 4], 'weight pattern')
        need(len(set(indices)) == 4 and all(1 <= i <= 9 for i in indices), 'index bounds/distinctness')
        rows = [palette[index * 12 + axis * 4:index * 12 + axis * 4 + 4]
                for index in indices for axis in range(3)]
        dots = []
        for row in rows:
            total = 0
            for a, b in zip(row, position):
                total += a * b
                maximum = max(maximum, a * b, total)
            dots.append(total)
        blend = []
        for axis in range(3):
            total = 0
            for bone in range(4):
                product = dots[bone * 3 + axis] * weights[bone]
                total += product
                maximum = max(maximum, product, total)
            blend.append(total)
        result.extend(blend + [1])
        for row in (1, 2, 10, 11):
            result.extend(rows[row])
        result.extend(dots[:3] + [1] + dots[9:12] + [1])
    need(maximum == 5350 and len(result) == 112, 'oracle maximum/shape')
    return struct.pack('<112I', *map(encode, result))


def csv_fixture(path, column):
    with path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    need(len(rows) == 112 and [int(r['word']) for r in rows] == list(range(112)), 'CSV word coverage')
    return struct.pack('<112I', *(int(r[column]) for r in rows))


def case_config(case='baseline'):
    need(case in CASES, 'INELIGIBLE: unknown case: ' + str(case))
    return dict(case=case, **CASES[case])


def input_identities(case='baseline'):
    config = case_config(case)
    pins = dict(PINS)
    pins[Path(config['shader']).name] = (config['bytes'], config['sha256'])
    return dict(case=config, pins=pins, hlsl=config['source_sha256'])


def preflight(case='baseline'):
    config = case_config(case)
    shader, source = ROOT / config['shader'], ROOT / config['source']
    need(shader.stat().st_size == config['bytes'], 'INELIGIBLE: selected shader size')
    need(source.stat().st_size <= 1024**2, 'INELIGIBLE: selected HLSL size')
    selected = shader.read_bytes()
    need(digest(selected) == config['sha256'], 'INELIGIBLE: selected shader identity')
    need(digest(source.read_bytes()) == config['source_sha256'], 'INELIGIBLE: selected HLSL identity')
    for path, limit in ((ROOT / 'data/baseline.dxil', 9796), (ROOT / 'source/baseline.hlsl', 1024**2),
                        (ROOT / 'evidence/nvidia-rtx5080.csv', 65536), (ROOT / 'evidence/expected.csv', 65536)):
        need(path.stat().st_size <= limit, 'INELIGIBLE: input size: ' + path.name)
    positions = ((1, 2, 3, 1), (2, 1, 4, 1), (3, 2, 1, 1), (1, 3, 2, 1))
    indices = ((1, 2, 3, 4), (4, 3, 2, 1), (7, 5, 9, 2), (2, 7, 1, 9))
    vb = b''.join(struct.pack('<8f4I', *p, 1, 2, 3, 4, *i) for p, i in zip(positions, indices))
    cb = struct.pack('<6144f', *range(1, 6145))
    data = {'synthetic-VB.bin': vb, 'synthetic-CB.bin': cb, 'oracle.bin': oracle(vb, cb),
            'known-bad.bin': csv_fixture(ROOT / 'evidence/nvidia-rtx5080.csv', 'observed_u32'),
            'baseline.dxil': (ROOT / 'data/baseline.dxil').read_bytes()}
    for name, (size, sha) in PINS.items():
        need(len(data[name]) == size and digest(data[name]) == sha, 'INELIGIBLE: input identity: ' + name)
    need(digest((ROOT / 'source/baseline.hlsl').read_bytes()) == HLSL_SHA, 'INELIGIBLE: HLSL identity')
    need(data['oracle.bin'] == csv_fixture(ROOT / 'evidence/expected.csv', 'expected_u32'), 'historical oracle CSV')
    data[shader.name] = selected
    return data


def finite(data):
    return len(data) % 4 == 0 and all(w & 0x7f800000 != 0x7f800000 for w in words(data))


def accounting(audit):
    return (len(audit) == 600 and audit[:64] == b'\xa5' * 64 and audit[512:576] == b'\xa5' * 64
            and struct.unpack_from('<3Q', audit, 576) == (448, 4, 4))


def classify(payload, good, bad, clean):
    if not clean or any(len(x) != 448 for x in (payload, good, bad)) or not finite(payload):
        return 'INCOMPLETE'
    return 'CORRECT' if payload == good else 'KNOWN_BAD' if payload == bad else 'OTHER_FINITE_MISMATCH'


def word_report(payload, good):
    need(len(payload) == len(good) == 448, 'word report shape')
    rows = []
    fields = ('SV_Position', 'ROW0', 'ROW1', 'ROW2', 'ROW3', 'RAW0', 'RAW1')
    for i, (a, b) in enumerate(zip(words(good), words(payload))):
        af, bf = (struct.unpack('<f', struct.pack('<I', w))[0] for w in (a, b))
        # JSON represents non-finite values as null; integer bits remain authoritative.
        rows.append(dict(word=i, vertex=i // 28, field=fields[i % 28 // 4], lane=i % 4,
                         expected_u32=a, observed_u32=b, expected_float=af,
                         observed_float=bf if b & 0x7f800000 != 0x7f800000 else None, equal=a == b))
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return rows, out.getvalue()


def select_adapter(keys, vendor=None, luid=None):
    need((vendor is None) != (luid is None), 'explicit hardware selection required')
    matches = [i for i, k in enumerate(keys) if not k['software'] and
               (k['vendor'] == vendor if vendor is not None else k['luid'] == luid)]
    need(matches, 'MISSING_ADAPTER')
    need(len(matches) == 1, 'AMBIGUOUS_ADAPTER: use --luid')
    return matches[0]


def allocation_total(previous, size, alignment):
    need(0 < size <= 128 * 1024**2 - previous and alignment > 0 and
         alignment & (alignment - 1) == 0 and size % alignment == 0, '128MiB allocation gate')
    return previous + size
