"""Pure-Python D3D12 reproducer: Windows x64, standard library and system DLLs only."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from fixtures import ROOT, PINS, HLSL_SHA, preflight, need, put, put_json, accounting, finite, classify, words, word_report

DEADLINE = 60.0
DRAIN_SECONDS = 5.0
OUTPUT_CAP = 64 * 1024**2
SOURCE_FILES = ('repro.py', 'fixtures.py', 'winabi.py', 'd3d12_host.py', 'cpu_tests.py',
                'source/baseline.hlsl', 'data/baseline.dxil', 'evidence/expected.csv', 'evidence/nvidia-rtx5080.csv')


def source_manifest():
    return {name: dict(bytes=(ROOT / name).stat().st_size,
                       sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest()) for name in SOURCE_FILES}


def luid(value):
    if not re.fullmatch(r'[0-9a-fA-F]{1,8}:[0-9a-fA-F]{1,8}', value):
        raise argparse.ArgumentTypeError('LUID requires HIGH:LOW, 1..8 hexadecimal digits each')
    return ':'.join(f'{int(x, 16):08x}' for x in value.split(':'))


def parse(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    argv = list(sys.argv[1:] if argv is None else argv)
    options = [arg.split('=', 1)[0] for arg in argv if arg.startswith('--')]
    if len(options) != len(set(options)):
        parser.error('each option may be specified only once')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help='NVIDIA and WARP, once each in separate Python children')
    group.add_argument('--vendor', choices=('nvidia', 'amd'))
    group.add_argument('--warp', action='store_true')
    group.add_argument('--luid', type=luid)
    group.add_argument('--list', action='store_true', help='explicit adapter inventory; creates a DXGI factory, no device')
    group.add_argument('--check-only', action='store_true', help='CPU checks only; no graphics DLL loading or enumeration')
    parser.add_argument('--output', type=Path, help='fresh session directory (default: unique folder under results/)')
    parser.add_argument('--_child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check_only and args.output:
        parser.error('--check-only does not accept --output')
    if args._child and (args.all or args.check_only or not args.output):
        parser.error('child requires one selector and a fresh output directory')
    return args


def child(args):
    args.output.mkdir()  # Parent directory exists; this directory must be fresh.
    put(args.output / 'STARTED.txt', 'INCOMPLETE until full raw gates and clean process exit are checked.\n')
    result = dict(classification='INCOMPLETE', numeric_interpretation=False, reason='preflight unfinished')
    try:
        files = preflight()
        from winabi import validate_platform
        validate_platform()
        put_json(args.output / 'source-manifest.json', source_manifest())
        for name, data in files.items():
            put(args.output / name, data)
        put(args.output / 'baseline.hlsl', (ROOT / 'source/baseline.hlsl').read_bytes())
        put_json(args.output / 'input-identities.json', dict(pins=PINS, hlsl=HLSL_SHA))
        from d3d12_host import graphics
        result = graphics(args, args.output, files)
    except Exception as error:
        result['reason'] = str(error)
    put_json(args.output / 'result.json', result)
    print(json.dumps(result), flush=True)
    return 0 if result.get('numeric_interpretation') or result['classification'] == 'LISTED' else 2 if result['classification'] == 'UNSUPPORTED' else 1


def output_size(folder):
    return sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())


def verify_numeric(output, result, files):
    """Parent independently validates the full raw evidence before accepting numbers."""
    need(result.get('numeric_interpretation') is True, 'child numeric gate')
    for name, data in files.items():
        need((output / name).read_bytes() == data, 'retained input ' + name)
    need((output / 'baseline.hlsl').read_bytes() == (ROOT / 'source/baseline.hlsl').read_bytes(), 'retained HLSL')
    for name in ('synthetic-VB.bin', 'synthetic-CB.bin'):
        need((output / (name + '.readback.bin')).read_bytes() == files[name], 'full input readback ' + name)
    audit = (output / 'BASELINE.audit.bin').read_bytes()
    payload = (output / 'BASELINE.outputs.bin').read_bytes()
    need(accounting(audit) and payload == audit[64:512] and finite(payload), 'raw audit/finite gate')
    for offset, label in ((0, 'position'), (16, 'second')):
        need((output / f'BASELINE.{label}.bin').read_bytes() ==
             b''.join(payload[i * 112 + offset:i * 112 + offset + 16] for i in range(4)), 'output projection')
    read_json = lambda name: json.loads((output / name).read_text(encoding='utf-8'))
    rows, csv = word_report(payload, files['oracle.bin'])
    need(read_json('words.json') == rows and (output / 'words.csv').read_bytes() == csv.encode(), 'full word reports')
    gates = read_json('raw-gates.json')
    allocations = read_json('allocations.json')
    need(gates['valid'] is True and gates['submissions_fenced'] == 2 and gates['draws'] == 1 and
         gates['allocation_requests'] == len(allocations) == 9, 'execution counts')
    from fixtures import allocation_total
    total = 0
    expected_requests = [(192, 2, 0xac3), (192, 1, 0x400), (192, 3, 0x400),
                         (24576, 2, 0xac3), (24576, 1, 0x400), (24576, 3, 0x400),
                         (600, 2, 0xac3), (600, 1, 0x400), (600, 3, 0x400)]
    for i, a in enumerate(allocations):
        request = read_json(f'ALLOCATION-request-{i}.json')
        need(all(request[k] == a[k] for k in request) and a['previous_total'] == total, 'allocation ledger')
        need((a['requested'], a['heap'], a['initial_state']) == expected_requests[i], 'allocation request route')
        total = allocation_total(total, a['allocation'], a['alignment'])
    need(total == gates['explicit_buffer_bytes'], 'allocation total')
    need(read_json('input-gate.json')['exact'] is True, 'input gate')
    for i in (1, 2):
        need(read_json(f'submission-{i}.json') == dict(fenced=True, serial=i), 'fenced submission')
    debug = read_json('debug-messages.json')
    status = read_json('debug-layer.json')['status']
    need(status in ('enabled', 'unavailable') and debug['available'] == (status == 'enabled') and
         debug['clean'] is True and all(m['severity'] not in (0, 1) for m in debug['messages']), 'debug gate')
    need(read_json('modules.json') and read_json('runtime.json') and read_json('adapter.json'), 'runtime identities')
    need(read_json('device.json')['hresult'] == 0, 'device creation evidence')
    sm = read_json('shader-model.json')
    need(sm['hresult'] == 0 and sm['requested'] == 0x68 and sm['reported'] >= 0x68, 'shader capability evidence')
    expected = classify(payload, files['oracle.bin'], files['known-bad.bin'], True)
    wrong = sum(a != b for a, b in zip(words(payload), words(files['oracle.bin'])))
    need(result['classification'] == expected and result['wrong_words'] == wrong and result['total_words'] == 112, 'classification')
    return True


@contextmanager
def deferred_cancellation():
    """Keep ownership during Popen's Windows handle registration and cleanup."""
    received, previous = [], {}
    def remember(number, frame):
        received.append(number)
    try:
        for number in (signal.SIGINT, getattr(signal, 'SIGBREAK', None)):
            if number is not None:
                previous[number] = signal.signal(number, remember)
        yield received
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def drain(process):
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=DRAIN_SECONDS)
        return None, process.poll() is not None
    except BaseException as error:
        return 'kill/drain failure: ' + repr(error), False


def supervise(process, folder, started, clock=time.monotonic, sleep=time.sleep, cancelled=None):
    """Regular files avoid pipe deadlocks; a child starts no grandchildren."""
    reason, drained = None, False
    try:
        while process.poll() is None:
            if cancelled:
                reason = 'parent cancellation'
                break
            if clock() - started >= DEADLINE:
                reason = '60-second deadline'
                break
            if output_size(folder) > OUTPUT_CAP:
                reason = '64MiB output limit'
                break
            sleep(0.05)
    except BaseException as error:
        reason = 'supervision exception: ' + repr(error)
    finally:
        cleanup_error, drained = drain(process)
        if cleanup_error:
            reason = cleanup_error
    if drained and output_size(folder) > OUTPUT_CAP:
        reason = '64MiB output limit'
    return reason, drained


def run_once(label, selector, session, files, manifest):
    # Windows signals become recorded cancellation until the child is owned,
    # drained, and its attempt record has been persisted.
    with deferred_cancellation() as cancelled:
        record = run_owned(label, selector, session, files, manifest, cancelled)
    # Handlers have now been restored: no deferred signal can arrive after
    # this check. A signal captured during persistence/restoration invalidates
    # the final session even if the earlier immutable snapshot was eligible.
    if cancelled:
        if 'parent cancellation' not in (record['supervision_error'] or ''):
            report_error(record, 'parent cancellation during finalization')
        record['superseding_outcome'] = 'supervision-cancelled.json'
        try:
            put_json(session / label / 'supervision-cancelled.json', record)
        except BaseException as error:
            report_error(record, 'cancellation persistence failure: ' + repr(error))
            stderr_best_effort('Cannot persist cancellation outcome: ' + repr(error))
    return record


def report_error(record, message):
    record['numeric_interpretation'] = False
    previous = record.get('supervision_error')
    record['supervision_error'] = (previous + '; ' if previous else '') + message


def stderr_best_effort(message):
    try:
        print(message, file=sys.stderr, flush=True)
    except BaseException:
        pass


def persist_record(folder, record):
    try:
        put_json(folder / 'supervision.json', record)
    except BaseException as error:
        report_error(record, 'supervision persistence failure: ' + repr(error))
        try:
            put_json(folder / 'supervision-failure.json', record)
        except BaseException as fallback:
            stderr_best_effort('Cannot persist attempt outcome: ' + repr(fallback))


def run_owned(label, selector, session, files, manifest, cancelled):
    folder = session / label
    folder.mkdir()
    output = folder / 'capture'
    started = time.monotonic()
    result, reason, drained, code = None, None, True, None
    process, supervised, logs, errors = None, False, [], []
    try:
        stdout = (folder / 'stdout.log').open('xb')
        logs.append(stdout)
        stderr = (folder / 'stderr.log').open('xb')
        logs.append(stderr)
        # The only runtime subprocess is this same interpreter running this same script.
        process = subprocess.Popen([sys.executable, '-E', '-s', str(ROOT / 'repro.py'), '--_child', *selector,
                                    '--output', str(output)], cwd=ROOT, stdout=stdout, stderr=stderr,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        reason, drained = supervise(process, folder, started, cancelled=cancelled)
        supervised = True
    except BaseException as error:
        reason = 'child launch/supervision failure: ' + repr(error)
    finally:
        if process is not None:
            if not supervised:
                cleanup_error, drained = drain(process)
                if cleanup_error:
                    errors.append(cleanup_error)
            code = process.returncode
        for log in logs:
            for operation in (log.flush, lambda log=log: os.fsync(log.fileno()), log.close):
                try:
                    operation()
                except BaseException as error:
                    errors.append('log finalization failure: ' + repr(error))
    if cancelled:
        errors.append('parent cancellation')
    numeric = False
    try:
        result = json.loads((output / 'result.json').read_text(encoding='utf-8'))
        if reason is None and not errors and drained and code == 0 and result.get('numeric_interpretation') is True:
            need(source_manifest() == manifest == json.loads((output / 'source-manifest.json').read_text()), 'source changed during run')
            numeric = verify_numeric(output, result, files)
            adapter = json.loads((output / 'adapter.json').read_text(encoding='utf-8'))
            if selector == ['--warp']:
                need(adapter['software'] is True, 'explicit WARP identity')
            else:
                need(adapter['software'] is False, 'explicit hardware identity')
                if selector[0] == '--vendor':
                    need(adapter['vendor'] == {'nvidia': 0x10de, 'amd': 0x1002}[selector[1]], 'vendor identity')
                else:
                    need(adapter['luid'] == selector[1], 'LUID identity')
    except BaseException as error:
        numeric = False
        if reason is None:
            reason = 'collection failure: ' + str(error)
    record = dict(selector=selector, exit=code, drained=drained, supervision_error=reason,
                  numeric_interpretation=numeric, result=result, output=str(output), seconds=time.monotonic() - started)
    for error in errors:
        report_error(record, error)
    try:
        if selector == ['--list'] and reason is None and not errors and drained and code == 0:
            print((output / 'adapters.json').read_text(encoding='utf-8'), flush=True)
        print(f'{label}: ' + (f"{result['classification']}, {result['wrong_words']}/112 wrong words" if record['numeric_interpretation'] else
                             f"{result.get('classification', 'INCOMPLETE') if result else 'INCOMPLETE'} (exit {code}); inspect logs"), flush=True)
    except BaseException as error:
        report_error(record, 'console reporting failure: ' + repr(error))
    if cancelled and 'parent cancellation' not in (record['supervision_error'] or ''):
        report_error(record, 'parent cancellation')
    persist_record(folder, record)
    return record


def save_summary(session, name, records):
    try:
        put_json(session / name, records)
        return True
    except BaseException as error:
        if records:
            report_error(records[-1], 'summary persistence failure: ' + repr(error))
        stderr_best_effort('Cannot persist ' + name + ': ' + repr(error))
        return False


def main(argv=None):
    args = parse(argv)
    if args._child:
        return child(args)
    if args.check_only:
        import cpu_tests
        return cpu_tests.run()
    from winabi import validate_platform
    validate_platform()
    files = preflight()  # Fail ineligible before launching any graphics child.
    manifest = source_manifest()
    session = (args.output or ROOT / 'results' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])).resolve()
    session.parent.mkdir(parents=True, exist_ok=True)
    session.mkdir()
    put_json(session / 'source-manifest.json', manifest)
    selections = [('nvidia', ['--vendor', 'nvidia']), ('warp', ['--warp'])]
    if not args.all:
        selections = [('list', ['--list'])] if args.list else [('luid', ['--luid', args.luid])] if args.luid else [
            (args.vendor, ['--vendor', args.vendor])] if args.vendor else [('warp', ['--warp'])]
    records = []
    summary_ok = False
    try:
        print(f'Results directory: {session}', flush=True)
        for label, selector in selections:
            record = run_once(label, selector, session, files, manifest)
            records.append(record)
            if not save_summary(session, f'summary-{len(records)}.json', records):
                break
            if record['supervision_error'] or not record['drained'] or record['exit'] not in (0, 1, 2):
                break
    finally:
        summary_ok = save_summary(session, 'summary.json', records)
    if not summary_ok or not records:
        return 1
    if args.list:
        return 0 if records[0]['exit'] == 0 and not records[0]['supervision_error'] else 1
    if len(records) != len(selections) or any(not r['numeric_interpretation'] for r in records):
        return 1
    return 2 if any(r['result']['wrong_words'] for r in records) else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
