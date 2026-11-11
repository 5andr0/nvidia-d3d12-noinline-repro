"""Graphics-free tests: no D3D12/DXGI DLL loading, enumeration or device calls."""
import ast
import contextlib
import ctypes as C
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import fixtures as f
import winabi as a


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = f.preflight()

    def test_exact_historical_fixtures(self):
        d = self.data
        self.assertEqual(f.oracle(d['synthetic-VB.bin'], d['synthetic-CB.bin']), d['oracle.bin'])
        self.assertEqual(f.csv_fixture(f.ROOT / 'evidence/warp.csv', 'observed_u32'), d['oracle.bin'])
        self.assertEqual(sum(x != y for x, y in zip(f.words(d['oracle.bin']), f.words(d['known-bad.bin']))), 48)
        self.assertEqual(struct.unpack_from('<4f', d['oracle.bin']), (2700, 2980, 3260, 1))
        for name, (size, sha) in f.PINS.items():
            self.assertEqual((len(d[name]), f.digest(d[name])), (size, sha))

    def test_oracle_rejects_bad_inputs(self):
        vb, cb = self.data['synthetic-VB.bin'], self.data['synthetic-CB.bin']
        for v, c in ((vb[:-1], cb), (vb[:32] + struct.pack('<I', 255) + vb[36:], cb),
                     (vb, struct.pack('<I', 0x7fc00000) + cb[4:]), (vb[:32] + vb[36:40] + vb[36:], cb)):
            with self.assertRaises(RuntimeError):
                f.oracle(v, c)
        for bits in (0, 0x7f800000, 0xff800000, 0x3fc00000, 0xbf800000):
            with self.assertRaises(RuntimeError):
                f.integer(bits)
        for n in (0, -1, 1 << 24):
            with self.assertRaises(RuntimeError):
                f.encode(n)

    def test_guards_counts_and_every_word_finiteness(self):
        good, bad = self.data['oracle.bin'], self.data['known-bad.bin']
        audit = b'\xa5' * 64 + good + b'\xa5' * 64 + struct.pack('<3Q', 448, 4, 4)
        self.assertTrue(f.accounting(audit))
        for at in (*range(64), *range(512, 600)):
            changed = bytearray(audit)
            changed[at] ^= 1
            self.assertFalse(f.accounting(changed), at)
        self.assertFalse(f.accounting(audit[:-1]))
        for i in range(112):
            for bits in (0x7f800000, 0xff800000, 0x7fc00001):
                changed = good[:i * 4] + struct.pack('<I', bits) + good[i * 4 + 4:]
                self.assertFalse(f.finite(changed))
                self.assertEqual(f.classify(changed, good, bad, True), 'INCOMPLETE')
        self.assertEqual(f.classify(good, good, bad, True), 'CORRECT')
        self.assertEqual(f.classify(bad, good, bad, True), 'KNOWN_BAD')
        changed = bytes([good[0] ^ 1]) + good[1:]
        self.assertEqual(f.classify(changed, good, bad, True), 'OTHER_FINITE_MISMATCH')
        self.assertEqual(f.classify(good, good, bad, False), 'INCOMPLETE')

    def test_reports_all_112_words(self):
        rows, text = f.word_report(self.data['known-bad.bin'], self.data['oracle.bin'])
        import csv
        parsed = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual([int(row['word']) for row in parsed], list(range(112)))
        self.assertEqual(sum(not r['equal'] for r in rows), 48)
        self.assertEqual({r['field'] for r in rows}, {'SV_Position', 'ROW0', 'ROW1', 'ROW2', 'ROW3', 'RAW0', 'RAW1'})
        self.assertEqual([r['observed_u32'] for r in rows], list(f.words(self.data['known-bad.bin'])))

    def test_allocation_budget(self):
        total = 0
        for _ in range(9):
            total = f.allocation_total(total, 65536, 65536)
        self.assertEqual(total, 589824)
        for previous, size, alignment in ((0, 2**64 - 1, 65536), (128 * 1024**2, 65536, 65536),
                                          (0, 0, 65536), (0, 65536, 0), (0, 65535, 65536), (0, 65536, 3)):
            with self.assertRaises(RuntimeError):
                f.allocation_total(previous, size, alignment)

    def test_selectors(self):
        import repro
        keys = [dict(vendor=0x10de, luid='00000000:00000001', software=False),
                dict(vendor=0x1002, luid='ffffffff:00000002', software=False),
                dict(vendor=0x10de, luid='00000000:00000003', software=True)]
        self.assertEqual(f.select_adapter(keys, 0x10de), 0)
        self.assertEqual(f.select_adapter(keys, luid='ffffffff:00000002'), 1)
        for collection in ([], keys + [keys[0]]):
            with self.assertRaises(RuntimeError):
                f.select_adapter(collection, 0x10de)
        self.assertEqual(repro.parse(['--luid', 'f:2']).luid, '0000000f:00000002')
        for args in ([], ['--warp', '--all'], ['--vendor', 'intel'], ['--luid', '-1:1'],
                     ['--luid', '100000000:0'], ['--luid', 'a:b:c'], ['--build-only'], ['--_child', '--all'],
                     ['--vendor', 'nvidia', '--vendor', 'amd'], ['--warp', '--output=x', '--output=y']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                repro.parse(args)

    def test_layout_contracts(self):
        # Values independently checked against the installed Microsoft SDK by a
        # private graphics-free compiler probe; no compiler is used by these tests.
        sizes = {'GUID': 16, 'LUID': 8, 'ResourceDesc': 56, 'Allocation': 16, 'Heap': 20,
                 'Barrier': 32, 'RootParameter': 32, 'RootDesc': 40, 'GraphicsPSO': 656,
                 'SOEntry': 24, 'InputElement': 32, 'AdapterDesc': 312, 'Message': 32, 'ModuleEntry': 1080}
        for name, size in sizes.items():
            self.assertEqual(C.sizeof(getattr(a, name)), size, name)
        offsets = {'ResourceDesc': {'Alignment': 8, 'Width': 16, 'SampleDesc': 36, 'Flags': 48},
                   'RootParameter': {'u': 8, 'ShaderVisibility': 24},
                   'GraphicsPSO': {'VS': 8, 'StreamOutput': 88, 'BlendState': 120, 'SampleMask': 448,
                                   'RasterizerState': 452, 'DepthStencilState': 496, 'InputLayout': 552,
                                   'CachedPSO': 632, 'Flags': 648},
                   'Message': {'pDescription': 16, 'DescriptionByteLength': 24}}
        for name, fields in offsets.items():
            for field, offset in fields.items():
                self.assertEqual(getattr(getattr(a, name), field).offset, offset, (name, field))

    def test_com_ownership_and_hidden_result_call(self):
        refs, observed = [2], []
        @a.CALL(a.U32, a.P)
        def release(this):
            refs[0] -= 1
            return refs[0]
        @a.CALL(a.P, a.P, a.PTR(a.Allocation), a.U32, a.U32, a.PTR(a.ResourceDesc))
        def allocation(this, output, mask, count, desc):
            observed.append((this, mask, count, desc.contents.Width))
            output.contents.SizeInBytes, output.contents.Alignment = 65536, 65536
            return C.addressof(output.contents)
        table = (a.P * 28)()
        table[2], table[25] = C.cast(release, a.P), C.cast(allocation, a.P)
        instance = C.pointer(table)
        pointer = C.cast(C.pointer(instance), a.P)
        first, second = a.Owner(pointer), a.Owner(pointer)
        result, desc = a.Allocation(), a.ResourceDesc(Width=600)
        returned = first.call('GetResourceAllocationInfo', a.ref(result), 0, 1, a.ref(desc))
        self.assertEqual(returned, C.addressof(result))
        self.assertEqual(observed, [(pointer.value, 0, 1, 600)])
        self.assertEqual(result.SizeInBytes, 65536)
        first.close()
        first.close()
        self.assertEqual(refs[0], 1)
        with self.assertRaises(RuntimeError):
            first.call('Release')
        second.close()
        self.assertEqual(refs[0], 0)

    def test_pending_failure_never_releases(self):
        import d3d12_host as host
        c = host.Context.__new__(host.Context)
        c.pending = True
        class Terminated(BaseException):
            pass
        with patch.object(host.os, '_exit', side_effect=Terminated) as terminate:
            with self.assertRaises(Terminated):
                c.close()
            terminate.assert_called_once_with(125)

    def test_submission_failure_terminates_before_unwind(self):
        import d3d12_host as host
        events = []
        class Fake:
            p = a.P(1)
            def call(self, name, *args):
                events.append(name)
                if name == 'Signal':
                    raise RuntimeError('injected queue failure')
        class Terminated(BaseException):
            pass
        c = host.Context.__new__(host.Context)
        c.pending, c.serial = False, 0
        c.commands = c.queue = c.fence = Fake()
        with patch.object(host.os, '_exit', side_effect=Terminated) as terminate:
            with self.assertRaises(Terminated):
                c.submit()
            terminate.assert_called_once_with(125)
        self.assertTrue(c.pending)
        self.assertEqual(events, ['Close', 'ExecuteCommandLists', 'Signal'])

    def test_parent_rejects_retained_input_corruption(self):
        import repro
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            # This is a CPU-only adversarial fixture, never a native capture.
            for name, data in self.data.items():
                f.put(folder / name, data)
            (folder / 'synthetic-VB.bin').write_bytes(bytes(192))
            with self.assertRaisesRegex(RuntimeError, 'retained input'):
                repro.verify_numeric(folder, {'numeric_interpretation': True}, self.data)

    def test_parent_deadline_drain_output_cap(self):
        import repro
        class Process:
            def __init__(self, fail=False):
                self.returncode, self.killed, self.fail = None, False, fail
            def poll(self):
                return self.returncode
            def kill(self):
                self.killed = True
                if self.fail:
                    raise OSError('injected kill failure')
                self.returncode = 125
            def wait(self, timeout):
                if self.fail:
                    raise TimeoutError('injected drain failure')
                return self.returncode
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            process = Process()
            reason, drained = repro.supervise(process, folder, 0, clock=lambda: 61)
            self.assertEqual(reason, '60-second deadline')
            self.assertTrue(drained and process.killed)
            reason, drained = repro.supervise(Process(True), folder, 0, clock=lambda: 61)
            self.assertIn('kill/drain failure', reason)
            self.assertFalse(drained)
            with patch.object(repro, 'output_size', return_value=repro.OUTPUT_CAP + 1):
                reason, drained = repro.supervise(Process(), folder, 0, clock=lambda: 0)
            self.assertEqual(reason, '64MiB output limit')
            self.assertTrue(drained)

    def test_parent_rejects_missing_result_and_nonzero_exit(self):
        import repro
        class Process:
            returncode = 125
            def poll(self):
                return self.returncode
            def wait(self, timeout):
                return self.returncode
        with tempfile.TemporaryDirectory() as d, patch.object(repro.subprocess, 'Popen', return_value=Process()) as spawn:
            with contextlib.redirect_stdout(io.StringIO()):
                record = repro.run_once('injected', ['--warp'], Path(d), self.data, {})
            self.assertFalse(record['numeric_interpretation'])
            self.assertTrue(record['drained'])
            self.assertEqual(record['exit'], 125)
            self.assertIn('collection failure', record['supervision_error'])
            argv = spawn.call_args.args[0]
            self.assertEqual(argv[0], repro.sys.executable)
            self.assertIn('--_child', argv)

    def test_runtime_has_no_compile_or_native_child(self):
        import repro
        calls = []
        for name in ('repro.py', 'fixtures.py', 'winabi.py', 'd3d12_host.py'):
            tree = ast.parse((f.ROOT / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess':
                        calls.append((name, node.func.attr))
                    self.assertNotEqual((getattr(node.func.value, 'id', None), node.func.attr), ('os', 'system'))
        self.assertEqual(calls, [('repro.py', 'Popen')])

    def test_cancellation_during_constructor_keeps_process_owned(self):
        import repro
        class Process:
            returncode = None
            def poll(self):
                return self.returncode
            def kill(self):
                self.returncode = 125
            def wait(self, timeout):
                self.assert_timeout = timeout
                return self.returncode
        process = Process()
        original = repro.signal.getsignal(repro.signal.SIGINT)
        def spawn(*args, **kwargs):
            # Model a real Windows SIGINT during Popen's constructor, before
            # assignment of its returned handle to the caller.
            repro.signal.getsignal(repro.signal.SIGINT)(repro.signal.SIGINT, None)
            return process
        with tempfile.TemporaryDirectory() as d, patch.object(repro.subprocess, 'Popen', side_effect=spawn):
            with contextlib.redirect_stdout(io.StringIO()):
                record = repro.run_once('interrupt', ['--warp'], Path(d), self.data, {})
            self.assertTrue(record['drained'])
            self.assertEqual(process.returncode, 125)
            self.assertEqual(process.assert_timeout, repro.DRAIN_SECONDS)
            self.assertIn('parent cancellation', record['supervision_error'])
            self.assertFalse(record['numeric_interpretation'])
            self.assertEqual(json.loads((Path(d) / 'interrupt/supervision-cancelled.json').read_text()), record)
        self.assertEqual(repro.signal.getsignal(repro.signal.SIGINT), original)

    def test_interruption_before_supervisor_entry_drains(self):
        import repro
        process = Mock(returncode=None)
        process.poll.side_effect = lambda: process.returncode
        process.kill.side_effect = lambda: setattr(process, 'returncode', 125)
        with tempfile.TemporaryDirectory() as d, patch.object(repro.subprocess, 'Popen', return_value=process), \
                patch.object(repro, 'supervise', side_effect=KeyboardInterrupt):
            with contextlib.redirect_stdout(io.StringIO()):
                record = repro.run_once('interrupt', ['--warp'], Path(d), self.data, {})
            process.kill.assert_called_once()
            process.wait.assert_called_once_with(timeout=repro.DRAIN_SECONDS)
            self.assertTrue(record['drained'])
            self.assertIn('KeyboardInterrupt', record['supervision_error'])
            self.assertFalse(record['numeric_interpretation'])

    def test_reporting_failures_still_persist_attempt_and_session(self):
        import repro
        # Deliberately mocked collection, not graphics evidence: establish a
        # numerically eligible control, then inject independent host failures.
        signals = ['cancel-SIGINT'] + (['cancel-SIGBREAK'] if hasattr(repro.signal, 'SIGBREAK') else [])
        for fault in ('none', 'flush', 'fsync', 'console', *signals):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                session = Path(d) / 'session'
                log_fds, proxies = set(), []
                spawns = []
                label = 'nvidia' if fault.startswith('cancel-') else 'warp'
                real_open, real_fsync = Path.open, repro.os.fsync
                def open_file(path, *args, **kwargs):
                    handle = real_open(path, *args, **kwargs)
                    if path.suffix == '.log' and args == ('xb',):
                        log_fds.add(handle.fileno())
                        if fault == 'flush':
                            wrapper = Mock(wraps=handle)
                            wrapper.flush.side_effect = OSError('injected log flush failure')
                            proxies.append(wrapper)
                            return wrapper
                    return handle
                def sync(fd):
                    if fault == 'fsync' and fd in log_fds:
                        # Remove it so later reused evidence-file descriptors
                        # remain writable and the finalization path is tested.
                        log_fds.remove(fd)
                        raise OSError('injected log fsync failure')
                    return real_fsync(fd)
                def spawn(argv, **kwargs):
                    spawns.append(argv)
                    out = Path(argv[-1])
                    out.mkdir()
                    f.put_json(out / 'result.json', dict(numeric_interpretation=True, classification='CORRECT', wrong_words=0))
                    f.put_json(out / 'source-manifest.json', {'mock': 'CPU-only'})
                    f.put_json(out / 'adapter.json', dict(software=False, vendor=0x10de) if label == 'nvidia' else dict(software=True))
                    process = Mock(returncode=0)
                    process.poll.return_value = 0
                    return process
                def progress(*args, **kwargs):
                    if fault == 'console' and str(args[0]).startswith('warp:'):
                        raise BrokenPipeError('injected progress failure')
                real_put = repro.put_json
                def persist(path, value):
                    real_put(path, value)
                    if fault.startswith('cancel-') and path.name == 'supervision.json':
                        number = getattr(repro.signal, fault[7:])
                        repro.signal.getsignal(number)(number, None)
                old_handlers = {n: repro.signal.getsignal(n) for n in
                                (repro.signal.SIGINT, getattr(repro.signal, 'SIGBREAK', repro.signal.SIGINT))}
                with patch.object(Path, 'open', open_file), patch.object(repro.os, 'fsync', side_effect=sync), \
                        patch.object(repro.subprocess, 'Popen', side_effect=spawn), \
                        patch.object(repro, 'source_manifest', return_value={'mock': 'CPU-only'}), \
                        patch.object(repro, 'verify_numeric', return_value=True), patch.object(repro, 'put_json', side_effect=persist), \
                        patch('builtins.print', side_effect=progress):
                    code = repro.main(['--all' if label == 'nvidia' else '--warp', '--output', str(session)])
                for number, previous in old_handlers.items():
                    self.assertEqual(repro.signal.getsignal(number), previous)
                final_name = 'supervision-cancelled.json' if fault.startswith('cancel-') else 'supervision.json'
                supervision = json.loads((session / label / final_name).read_text())
                self.assertEqual(len(spawns), 1)
                self.assertEqual(json.loads((session / 'summary-1.json').read_text()), [supervision])
                self.assertEqual(json.loads((session / 'summary.json').read_text()), [supervision])
                self.assertTrue(supervision['drained'])
                if fault == 'none':
                    self.assertEqual(code, 0)
                    self.assertTrue(supervision['numeric_interpretation'])
                else:
                    self.assertEqual(code, 1)
                    self.assertFalse(supervision['numeric_interpretation'])
                    self.assertIn('cancellation' if fault.startswith('cancel-') else 'failure', supervision['supervision_error'])
                for proxy in proxies:
                    proxy.close.assert_called_once()

    def test_supervision_persistence_failure_has_fallback(self):
        import repro
        record = dict(numeric_interpretation=True, supervision_error=None, drained=True)
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            real_put = repro.put_json
            def fail_first(path, value):
                if path.name == 'supervision.json':
                    raise OSError('injected evidence write failure')
                real_put(path, value)
            with patch.object(repro, 'put_json', side_effect=fail_first):
                repro.persist_record(folder, record)
            self.assertFalse(record['numeric_interpretation'])
            self.assertEqual(json.loads((folder / 'supervision-failure.json').read_text()), record)

    def test_session_stops_after_reporting_failure(self):
        import repro
        record = dict(numeric_interpretation=False, supervision_error='console reporting failure',
                      drained=True, exit=0)
        with tempfile.TemporaryDirectory() as d, patch.object(repro, 'run_once', return_value=record) as attempt, \
                contextlib.redirect_stdout(io.StringIO()):
            session = Path(d) / 'session'
            self.assertEqual(repro.main(['--all', '--output', str(session)]), 1)
            attempt.assert_called_once()
            self.assertEqual(attempt.call_args.args[:2], ('nvidia', ['--vendor', 'nvidia']))
            self.assertEqual(json.loads((session / 'summary.json').read_text()), [record])

    def test_default_controls_are_nvidia_and_warp_only(self):
        import repro
        def outcome(label, selector, *args):
            return dict(selector=selector, numeric_interpretation=True, supervision_error=None,
                        drained=True, exit=0, result=dict(wrong_words=0))
        with tempfile.TemporaryDirectory() as d, patch.object(repro, 'run_once', side_effect=outcome) as attempt, \
                contextlib.redirect_stdout(io.StringIO()):
            session = Path(d) / 'session'
            self.assertEqual(repro.main(['--all', '--output', str(session)]), 0)
            self.assertEqual([call.args[:2] for call in attempt.call_args_list],
                             [('nvidia', ['--vendor', 'nvidia']), ('warp', ['--warp'])])
            self.assertEqual(len(json.loads((session / 'summary.json').read_text())), 2)


def run():
    a.validate_platform()
    # Fail immediately if any test accidentally attempts a system/graphics DLL load.
    with patch.object(C, 'WinDLL', side_effect=AssertionError('CPU checks must not load DLLs')):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(run())
