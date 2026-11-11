"""Direct ctypes D3D12 vertex/stream-output route. Called only in a supervised child."""
import ctypes as C
import hashlib
import os
import sys
from pathlib import Path
from fixtures import (need, put, put_json, digest, words, finite, accounting, classify,
                      word_report, select_adapter, allocation_total, case_config)
from winabi import (U32, U64, P, SZ, ref, IIDS, Libraries, Owner, method, hr, wide,
    AdapterDesc, ModuleEntry, Message, ResourceDesc, Heap, Sample, Allocation, Range,
    Barrier, Transition, QueueDesc, QueryDesc, RootParameter, RootDesc, RootDescriptor,
    InputElement, SOEntry, SODesc, InputLayout, Bytecode, GraphicsPSO, Stencil, VBView, SOView)

COPY_DEST, COPY_SOURCE, VERTEX_CB, STREAM_OUT, GENERIC_READ = 0x400, 0x800, 1, 0x100, 0xac3


class Unsupported(RuntimeError):
    pass


class Context:
    def __init__(self, out):
        self.out, self.owners, self.resources = out, [], []
        self.pending, self.serial, self.allocated = False, 0, 0
        self.allocations, self.event = [], None
        self.info = None
        self.debug_status = 'unavailable'
        self.api = Libraries()

    def own(self, pointer):
        obj = Owner(pointer)
        self.owners.append(obj)
        return obj

    def create(self, obj, name, iid, *args):
        pointer = P()
        obj.call(name, *args, ref(IIDS[iid]), ref(pointer))
        return self.own(pointer)

    def close(self):
        # Never unwind COM/resource lifetimes while an unfenced submission may use them.
        if self.pending:
            os._exit(125)
        for obj in reversed(self.owners):
            obj.close()
        if self.event:
            need(self.api.close_handle(self.event), 'CloseHandle fence event')
            self.event = None

    def buffer(self, size, heap_type, state, name):
        need(len(self.allocations) < 9 and 0 < size <= 24576, 'buffer request bound')
        desc = ResourceDesc(Dimension=1, Width=size, Height=1, DepthOrArraySize=1,
                            MipLevels=1, SampleDesc=Sample(1, 0), Layout=1)
        allocation = Allocation()
        returned = self.device.call('GetResourceAllocationInfo', ref(allocation), 0, 1, ref(desc))
        need(returned == C.addressof(allocation), 'allocation hidden result pointer')
        record = dict(name=name, requested=size, allocation=allocation.SizeInBytes,
                      alignment=allocation.Alignment, previous_total=self.allocated, heap=heap_type, initial_state=state)
        put_json(self.out / f'ALLOCATION-request-{len(self.allocations)}.json', record)
        self.allocated = allocation_total(self.allocated, allocation.SizeInBytes, allocation.Alignment)
        hp = Heap(heap_type, 0, 0, 1, 1)
        obj = self.create(self.device, 'CreateCommittedResource', 'Resource', ref(hp), 0, ref(desc), state, None)
        obj.size, obj.state, obj.heap = size, state, heap_type
        record['gpu_address'] = obj.call('GetGPUVirtualAddress')
        self.allocations.append(record)
        self.resources.append(obj)
        return obj

    def transition(self, obj, before, after):
        need(obj.state == before and obj.heap == 1, 'resource state tracking')
        barrier = Barrier()
        barrier.u.Transition = Transition(obj.p, 0xffffffff, before, after)
        self.commands.call('ResourceBarrier', 1, ref(barrier))
        obj.state = after

    def copy(self, dest, source, size):
        need(dest.state == COPY_DEST and source.state in (COPY_SOURCE, GENERIC_READ)
             and size <= min(dest.size, source.size), 'copy resource bounds/states')
        self.commands.call('CopyBufferRegion', dest.p, 0, source.p, 0, size)

    def submit(self):
        need(not self.pending and self.serial < 2, 'submission bound')
        self.commands.call('Close')
        lists = (P * 1)(self.commands.p)
        self.pending = True
        try:
            self.queue.call('ExecuteCommandLists', 1, lists)
            self.serial += 1
            self.queue.call('Signal', self.fence.p, self.serial)
            self.fence.call('SetEventOnCompletion', self.serial, self.event)
            need(self.api.wait(self.event, 10000) == 0, '10-second native fence wait failed/timed out')
            completed = self.fence.call('GetCompletedValue')
            need(completed != (1 << 64) - 1 and completed >= self.serial, 'removed/incomplete fence')
            self.pending = False
        except BaseException:
            # No Python cleanup, logging, flush or COM Release on this path.
            os._exit(125)
        put_json(self.out / f'submission-{self.serial}.json', dict(fenced=True, serial=self.serial))

    def reset(self):
        need(not self.pending and self.serial == 1, 'allocator reuse requires first completed fence')
        self.allocator.call('ResetAllocator')
        self.commands.call('ResetList', self.allocator.p, None)


def upload(obj, data):
    need(obj.heap == 2 and len(data) == obj.size, 'upload size/heap')
    pointer = P()
    obj.call('Map', 0, ref(Range(0, 0)), ref(pointer))
    try:
        need(bool(pointer), 'null upload mapping')
        C.memmove(pointer, data, len(data))
    finally:
        obj.call('Unmap', 0, ref(Range(0, len(data))))


def download(obj):
    need(obj.heap == 3 and obj.state == COPY_DEST, 'readback heap/state')
    pointer = P()
    obj.call('Map', 0, ref(Range(0, obj.size)), ref(pointer))
    try:
        need(bool(pointer), 'null readback mapping')
        return C.string_at(pointer, obj.size)
    finally:
        obj.call('Unmap', 0, ref(Range(0, 0)))


def description(adapter):
    desc = AdapterDesc()
    adapter.call('GetDesc1', ref(desc))
    return dict(name=wide(desc.Description), vendor=desc.VendorId, device=desc.DeviceId,
                subsystem=desc.SubSysId, revision=desc.Revision, software=bool(desc.Flags & 2),
                luid=f'{desc.AdapterLuid.HighPart & 0xffffffff:08x}:{desc.AdapterLuid.LowPart:08x}')


def choose(c, args):
    pointer = P()
    hr(c.api.create_factory(0, ref(IIDS['Factory']), ref(pointer)), 'CreateDXGIFactory2')
    factory = c.own(pointer)
    if args.warp:
        adapter = c.create(factory, 'EnumWarpAdapter', 'Adapter')
        need(description(adapter)['software'], 'WARP must be software')
        return adapter
    adapters, keys = [], []
    for index in range(128):
        pointer = P()
        status = method(factory.p, 'EnumAdapters1', index, ref(pointer))
        if status & 0xffffffff == 0x887a0002:
            break
        hr(status, 'EnumAdapters1')
        adapter = c.own(pointer)
        adapters.append(adapter)
        keys.append(description(adapter))
    else:
        raise RuntimeError('adapter enumeration cap')
    put_json(c.out / 'adapters.json', keys)
    if args.list:
        print(__import__('json').dumps(keys, indent=2), flush=True)
        return None
    vendor = {'nvidia': 0x10de, 'amd': 0x1002}.get(args.vendor)
    return adapters[select_adapter(keys, vendor, args.luid)]


def debug_messages(c):
    if c.info is None:
        put_json(c.out / 'debug-messages.json', dict(available=False, messages=[], clean=True))
        return True
    count = c.info.call('GetNumStoredMessages')
    need(count <= 4096 and c.info.call('GetNumMessagesDiscardedByMessageCountLimit') == 0, 'debug capture overflow')
    rows, description_bytes = [], 0
    for i in range(count):
        size = SZ()
        c.info.call('GetMessage', i, None, ref(size))
        need(C.sizeof(Message) <= size.value <= 65536, 'debug message size')
        storage = C.create_string_buffer(size.value)
        capacity = size.value
        c.info.call('GetMessage', i, storage, ref(size))
        need(size.value <= capacity, 'debug message growth')
        message = Message.from_buffer(storage)
        start, end = C.addressof(storage), C.addressof(storage) + capacity
        need(message.pDescription is not None and start <= message.pDescription <= end and
             message.DescriptionByteLength <= end - message.pDescription, 'debug description bounds')
        description_bytes += message.DescriptionByteLength
        need(description_bytes <= 4 * 1024**2, 'debug capture byte cap')
        rows.append(dict(severity=message.Severity, id=message.ID,
                         description=C.string_at(message.pDescription, message.DescriptionByteLength).decode('utf-8', 'replace')))
    clean = all(row['severity'] not in (0, 1) for row in rows)
    put_json(c.out / 'debug-messages.json', dict(available=True, messages=rows, clean=clean))
    return clean


def modules(c):
    handle = c.api.snapshot(8, os.getpid())
    need(handle not in (None, P(-1).value), 'module snapshot')
    result = []
    try:
        entry = ModuleEntry()
        entry.dwSize = C.sizeof(entry)
        more = c.api.module_first(handle, ref(entry))
        need(more, 'module first')
        while more:
            need(len(result) < 256, 'module count bound')
            path = Path(wide(entry.szExePath))
            size = path.stat().st_size
            need(size <= 512 * 1024**2, 'module size bound')
            sha, total = hashlib.sha256(), 0
            with path.open('rb') as f:
                while True:
                    block = f.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    need(total <= size, 'module changed during read')
                    sha.update(block)
            need(total == size, 'module short read')
            result.append(dict(path=str(path), bytes=size, sha256=sha.hexdigest()))
            more = c.api.module_next(handle, ref(entry))
        need(C.get_last_error() == 18, 'module enumeration failure')
    finally:
        need(c.api.close_handle(handle), 'close module snapshot')
    put_json(c.out / 'modules.json', result)
    put_json(c.out / 'runtime.json', dict(python=sys.version, executable=sys.executable,
                                       windows=list(sys.getwindowsversion()), pid=os.getpid()))


def pipeline(c, shader):
    parameters = (RootParameter * 3)()
    for i, param in enumerate(parameters):
        param.ParameterType, param.ShaderVisibility = 2, 1
        param.u.Descriptor = RootDescriptor(i, 0)
    desc = RootDesc(3, parameters, 0, None, 0x41)
    blob, error = P(), P()
    status = c.api.serialize(ref(desc), 1, ref(blob), ref(error))
    root_bytes = c.own(blob) if blob else None
    error_bytes = c.own(error) if error else None
    if error_bytes:
        size = error_bytes.call('GetBufferSize')
        need(size <= 1024**2, 'root error bound')
        put(c.out / 'BASELINE.root-errors.bin', C.string_at(error_bytes.call('GetBufferPointer'), size))
    hr(status, 'D3D12SerializeRootSignature')
    need(root_bytes is not None, 'missing root signature bytes')
    size = root_bytes.call('GetBufferSize')
    need(0 < size <= 1024**2, 'root byte bound')
    pointer = root_bytes.call('GetBufferPointer')
    put(c.out / 'BASELINE.root.bin', C.string_at(pointer, size))
    root = c.create(c.device, 'CreateRootSignature', 'Root', 0, pointer, size)
    inputs = (InputElement * 3)(InputElement(b'POS', 0, 2, 0, 0, 0, 0),
        InputElement(b'WEIGHT', 0, 2, 0, 16, 0, 0), InputElement(b'INDEX', 0, 3, 0, 32, 0, 0))
    entries = (SOEntry * 7)(SOEntry(0, b'SV_Position', 0, 0, 4, 0),
        *(SOEntry(0, b'ROW', i, 0, 4, 0) for i in range(4)), *(SOEntry(0, b'RAW', i, 0, 4, 0) for i in range(2)))
    stride = U32(112)
    shader_storage = C.create_string_buffer(shader)
    pso = GraphicsPSO()
    pso.pRootSignature = root.p
    pso.VS = Bytecode(C.cast(shader_storage, P), len(shader))
    pso.InputLayout = InputLayout(inputs, 3)
    pso.StreamOutput = SODesc(entries, 7, C.pointer(stride), 1, 0xffffffff)
    pso.SampleMask, pso.PrimitiveTopologyType, pso.SampleDesc.Count = 0xffffffff, 1, 1
    pso.RasterizerState.FillMode, pso.RasterizerState.CullMode, pso.RasterizerState.DepthClipEnable = 3, 1, 1
    pso.DepthStencilState.DepthFunc = 8
    pso.DepthStencilState.FrontFace = pso.DepthStencilState.BackFace = Stencil(1, 1, 1, 8)
    for rt in pso.BlendState.RenderTarget:
        rt.SrcBlend = rt.SrcBlendAlpha = 2
        rt.DestBlend = rt.DestBlendAlpha = rt.BlendOp = rt.BlendOpAlpha = 1
        rt.LogicOp, rt.RenderTargetWriteMask = 4, 15
    state = c.create(c.device, 'CreateGraphicsPipelineState', 'PSO', ref(pso))
    return root, state


def execute(c, files, case='baseline'):
    c.queue = c.create(c.device, 'CreateCommandQueue', 'Queue', ref(QueueDesc()))
    c.allocator = c.create(c.device, 'CreateCommandAllocator', 'Allocator', 0)
    c.commands = c.create(c.device, 'CreateCommandList', 'List', 0, 0, c.allocator.p, None)
    c.fence = c.create(c.device, 'CreateFence', 'Fence', 0, 0)
    queries = c.create(c.device, 'CreateQueryHeap', 'Query', ref(QueryDesc(3, 1, 0)))
    c.event = c.api.create_event(None, 0, 0, None)
    need(c.event, 'fence event creation')
    inputs, readbacks = [], []
    for name in ('synthetic-VB.bin', 'synthetic-CB.bin'):
        data = files[name]
        source = c.buffer(len(data), 2, GENERIC_READ, name + ' upload')
        upload(source, data)
        dest = c.buffer(len(data), 1, COPY_DEST, name + ' device')
        readback = c.buffer(len(data), 3, COPY_DEST, name + ' readback')
        c.copy(dest, source, len(data))
        c.transition(dest, COPY_DEST, COPY_SOURCE)
        c.copy(readback, dest, len(data))
        c.transition(dest, COPY_SOURCE, VERTEX_CB)
        inputs.append(dest)
        readbacks.append((name, readback))
    c.submit()
    exact = True
    for name, readback in readbacks:
        data = download(readback)
        put(c.out / (name + '.readback.bin'), data)
        exact = exact and data == files[name]
    put_json(c.out / 'input-gate.json', dict(exact=exact))
    need(exact, 'GPU input readback mismatch; PSO not created')
    c.reset()
    seed = c.buffer(600, 2, GENERIC_READ, 'SO seed')
    upload(seed, b'\xa5' * 576 + bytes(24))
    root, pso = pipeline(c, files[Path(case_config(case)['shader']).name])
    output = c.buffer(600, 1, COPY_DEST, 'SO output')
    readback = c.buffer(600, 3, COPY_DEST, 'SO readback')
    put_json(c.out / 'allocations.json', c.allocations)
    c.copy(output, seed, 600)
    c.transition(output, COPY_DEST, STREAM_OUT)
    commands = c.commands
    commands.call('SetPipelineState', pso.p)
    commands.call('SetGraphicsRootSignature', root.p)
    commands.call('IASetPrimitiveTopology', 1)
    view = VBView(inputs[0].call('GetGPUVirtualAddress'), 192, 48)
    commands.call('IASetVertexBuffers', 0, 1, ref(view))
    cb_address = inputs[1].call('GetGPUVirtualAddress')
    need(cb_address != 0 and cb_address % 256 == 0, 'CBV alignment')
    for i in range(3):
        commands.call('SetGraphicsRootConstantBufferView', i, cb_address)
    address = output.call('GetGPUVirtualAddress')
    so = SOView(address + 64, 448, address + 576)
    commands.call('SOSetTargets', 0, 1, ref(so))
    commands.call('BeginQuery', queries.p, 4, 0)
    commands.call('DrawInstanced', 4, 1, 0, 0)
    commands.call('EndQuery', queries.p, 4, 0)
    commands.call('SOSetTargets', 0, 0, None)
    c.transition(output, STREAM_OUT, COPY_SOURCE)
    c.copy(readback, output, 600)
    commands.call('ResolveQueryData', queries.p, 4, 0, 1, readback.p, 584)
    c.submit()
    audit = download(readback)
    payload = audit[64:512]
    put(c.out / 'BASELINE.audit.bin', audit)
    put(c.out / 'BASELINE.outputs.bin', payload)
    for offset, label in ((0, 'position'), (16, 'second')):
        put(c.out / f'BASELINE.{label}.bin', b''.join(payload[v * 112 + offset:v * 112 + offset + 16] for v in range(4)))
    rows, csv = word_report(payload, files['oracle.bin'])
    put(c.out / 'words.csv', csv)
    put_json(c.out / 'words.json', rows)
    valid = accounting(audit) and finite(payload) and len(c.allocations) == 9 and c.serial == 2
    put_json(c.out / 'raw-gates.json', dict(valid=valid, accounting=accounting(audit), finite_all_112=finite(payload),
             submissions_fenced=c.serial, draws=1, explicit_buffer_bytes=c.allocated, allocation_requests=len(c.allocations)))
    # Release GPU objects after completed fences, before inspecting the debug queue.
    for obj in reversed(c.owners[c.owners.index(c.queue):]):
        obj.close()
    c.device.call('GetDeviceRemovedReason')
    return payload, valid


def graphics(args, out, files):
    c = Context(out)
    result = dict(classification='INCOMPLETE', numeric_interpretation=False, wrong_words=None, total_words=112,
                  requires_exit_zero_for_numeric_interpretation=True)
    try:
        if not args.list:
            pointer = P()
            status = c.api.get_debug(ref(IIDS['Debug']), ref(pointer))
            if status >= 0:
                c.own(pointer).call('EnableDebugLayer')
                c.debug_status = 'enabled'
            put_json(out / 'debug-layer.json', dict(status=c.debug_status, hresult=status & 0xffffffff))
        adapter = choose(c, args)
        if args.list:
            result.update(classification='LISTED', reason='explicit adapter inventory; no device created')
            return result
        identity = description(adapter)
        driver = C.c_int64()
        status = method(adapter.p, 'CheckInterfaceSupport', ref(IIDS['DXGIDevice']), ref(driver))
        identity.update(driver_query_hresult=status & 0xffffffff, driver_version_raw=driver.value if status >= 0 else None)
        put_json(out / 'adapter.json', identity)
        pointer = P()
        status = c.api.create_device(adapter.p, 0xc000, ref(IIDS['Device']), ref(pointer))
        put_json(out / 'device.json', dict(hresult=status & 0xffffffff))
        if status & 0xffffffff == 0x887a0004:
            raise Unsupported('feature level 12.0 unavailable')
        hr(status, 'D3D12CreateDevice')
        c.device = c.own(pointer)
        if c.debug_status == 'enabled':
            c.info = c.create(c.device, 'QueryInterface', 'Info')
            c.info.call('SetMessageCountLimit', 4096)
        sm = U32(0x68)
        status = method(c.device.p, 'CheckFeatureSupport', 7, ref(sm), C.sizeof(sm))
        put_json(out / 'shader-model.json', dict(requested=0x68, reported=sm.value, hresult=status & 0xffffffff))
        if status & 0xffffffff in (0x80070057, 0x887a0004) or (status >= 0 and sm.value < 0x68):
            raise Unsupported('shader model 6.8 unavailable; shader unchanged')
        hr(status, 'CheckFeatureSupport')
        payload, valid = execute(c, files, args.case)
        clean = debug_messages(c)
        modules(c)
        classification = classify(payload, files['oracle.bin'], files['known-bad.bin'], valid and clean)
        numeric = classification != 'INCOMPLETE'
        result.update(classification=classification, numeric_interpretation=numeric,
                      wrong_words=sum(a != b for a, b in zip(words(payload), words(files['oracle.bin']))) if numeric else None,
                      reason='complete raw gates and debug capture' if numeric else 'invalid raw/debug gates')
    except Exception as error:
        result.update(classification='UNSUPPORTED' if isinstance(error, Unsupported) else 'INCOMPLETE', reason=str(error))
        try:
            if not (out / 'debug-messages.json').exists():
                need(debug_messages(c), 'severe debug messages')
            if not (out / 'modules.json').exists():
                modules(c)
        except Exception as capture_error:
            result.update(classification='INCOMPLETE', reason=f'{error}; evidence capture: {capture_error}')
    finally:
        c.close()
    result['debug_layer'] = c.debug_status
    return result
