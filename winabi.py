"""Minimal authored Windows x64 ABI declarations. Importing loads no graphics DLL.

Contracts: Windows SDK 10.0.26100.0 d3d12.h, d3d12sdklayers.h,
dxgi.h/dxgi1_4.h, d3dcommon.h and TlHelp32.h. See ABI.md.
"""
import ctypes as C
import platform
import sys
import uuid
from fixtures import need

U8, U16, U32, U64 = C.c_uint8, C.c_uint16, C.c_uint32, C.c_uint64
I32, F32, P, SZ = C.c_int32, C.c_float, C.c_void_p, C.c_size_t
PTR, ref = C.POINTER, C.byref
CALL = getattr(C, 'WINFUNCTYPE', C.CFUNCTYPE)


def struct_type(name, fields, base=C.Structure):
    return type(name, (base,), {'_fields_': fields})


GUID = struct_type('GUID', [('Data1', U32), ('Data2', U16), ('Data3', U16), ('Data4', U8 * 8)])
LUID = struct_type('LUID', [('LowPart', U32), ('HighPart', I32)])
Sample = struct_type('Sample', [('Count', U32), ('Quality', U32)])
Range = struct_type('Range', [('Begin', SZ), ('End', SZ)])
Allocation = struct_type('Allocation', [('SizeInBytes', U64), ('Alignment', U64)])
Heap = struct_type('Heap', [('Type', U32), ('CPUPageProperty', U32), ('MemoryPoolPreference', U32),
                          ('CreationNodeMask', U32), ('VisibleNodeMask', U32)])
ResourceDesc = struct_type('ResourceDesc', [('Dimension', U32), ('Alignment', U64), ('Width', U64),
    ('Height', U32), ('DepthOrArraySize', U16), ('MipLevels', U16), ('Format', U32),
    ('SampleDesc', Sample), ('Layout', U32), ('Flags', U32)])
Transition = struct_type('Transition', [('pResource', P), ('Subresource', U32), ('StateBefore', U32), ('StateAfter', U32)])
BarrierUnion = struct_type('BarrierUnion', [('Transition', Transition), ('Aliasing', P * 2), ('UAV', P)], C.Union)
Barrier = struct_type('Barrier', [('Type', U32), ('Flags', U32), ('u', BarrierUnion)])
QueueDesc = struct_type('QueueDesc', [('Type', U32), ('Priority', I32), ('Flags', U32), ('NodeMask', U32)])
QueryDesc = struct_type('QueryDesc', [('Type', U32), ('Count', U32), ('NodeMask', U32)])
VBView = struct_type('VBView', [('BufferLocation', U64), ('SizeInBytes', U32), ('StrideInBytes', U32)])
SOView = struct_type('SOView', [('BufferLocation', U64), ('SizeInBytes', U64), ('BufferFilledSizeLocation', U64)])
RootTable = struct_type('RootTable', [('NumDescriptorRanges', U32), ('pDescriptorRanges', P)])
RootConstants = struct_type('RootConstants', [('ShaderRegister', U32), ('RegisterSpace', U32), ('Num32BitValues', U32)])
RootDescriptor = struct_type('RootDescriptor', [('ShaderRegister', U32), ('RegisterSpace', U32)])
RootUnion = struct_type('RootUnion', [('DescriptorTable', RootTable), ('Constants', RootConstants), ('Descriptor', RootDescriptor)], C.Union)
RootParameter = struct_type('RootParameter', [('ParameterType', U32), ('u', RootUnion), ('ShaderVisibility', U32)])
RootDesc = struct_type('RootDesc', [('NumParameters', U32), ('pParameters', PTR(RootParameter)),
    ('NumStaticSamplers', U32), ('pStaticSamplers', P), ('Flags', U32)])
Bytecode = struct_type('Bytecode', [('pShaderBytecode', P), ('BytecodeLength', SZ)])
SOEntry = struct_type('SOEntry', [('Stream', U32), ('SemanticName', C.c_char_p), ('SemanticIndex', U32),
    ('StartComponent', U8), ('ComponentCount', U8), ('OutputSlot', U8)])
SODesc = struct_type('SODesc', [('pSODeclaration', PTR(SOEntry)), ('NumEntries', U32),
    ('pBufferStrides', PTR(U32)), ('NumStrides', U32), ('RasterizedStream', U32)])
InputElement = struct_type('InputElement', [('SemanticName', C.c_char_p), ('SemanticIndex', U32),
    ('Format', U32), ('InputSlot', U32), ('AlignedByteOffset', U32), ('InputSlotClass', U32), ('InstanceDataStepRate', U32)])
InputLayout = struct_type('InputLayout', [('pInputElementDescs', PTR(InputElement)), ('NumElements', U32)])
RTBlend = struct_type('RTBlend', [(n, I32 if n.endswith('Enable') else U32) for n in
    ('BlendEnable', 'LogicOpEnable', 'SrcBlend', 'DestBlend', 'BlendOp', 'SrcBlendAlpha', 'DestBlendAlpha', 'BlendOpAlpha', 'LogicOp')]
    + [('RenderTargetWriteMask', U8)])
Blend = struct_type('Blend', [('AlphaToCoverageEnable', I32), ('IndependentBlendEnable', I32), ('RenderTarget', RTBlend * 8)])
Rasterizer = struct_type('Rasterizer', [('FillMode', U32), ('CullMode', U32), ('FrontCounterClockwise', I32),
    ('DepthBias', I32), ('DepthBiasClamp', F32), ('SlopeScaledDepthBias', F32), ('DepthClipEnable', I32),
    ('MultisampleEnable', I32), ('AntialiasedLineEnable', I32), ('ForcedSampleCount', U32), ('ConservativeRaster', U32)])
Stencil = struct_type('Stencil', [(n, U32) for n in ('StencilFailOp', 'StencilDepthFailOp', 'StencilPassOp', 'StencilFunc')])
DepthStencil = struct_type('DepthStencil', [('DepthEnable', I32), ('DepthWriteMask', U32), ('DepthFunc', U32),
    ('StencilEnable', I32), ('StencilReadMask', U8), ('StencilWriteMask', U8), ('FrontFace', Stencil), ('BackFace', Stencil)])
CachedPSO = struct_type('CachedPSO', [('pCachedBlob', P), ('CachedBlobSizeInBytes', SZ)])
GraphicsPSO = struct_type('GraphicsPSO', [('pRootSignature', P)] + [(n, Bytecode) for n in ('VS', 'PS', 'DS', 'HS', 'GS')] + [
    ('StreamOutput', SODesc), ('BlendState', Blend), ('SampleMask', U32), ('RasterizerState', Rasterizer),
    ('DepthStencilState', DepthStencil), ('InputLayout', InputLayout), ('IBStripCutValue', U32),
    ('PrimitiveTopologyType', U32), ('NumRenderTargets', U32), ('RTVFormats', U32 * 8), ('DSVFormat', U32),
    ('SampleDesc', Sample), ('NodeMask', U32), ('CachedPSO', CachedPSO), ('Flags', U32)])
AdapterDesc = struct_type('AdapterDesc', [('Description', U16 * 128), ('VendorId', U32), ('DeviceId', U32),
    ('SubSysId', U32), ('Revision', U32), ('DedicatedVideoMemory', SZ), ('DedicatedSystemMemory', SZ),
    ('SharedSystemMemory', SZ), ('AdapterLuid', LUID), ('Flags', U32)])
Message = struct_type('Message', [('Category', U32), ('Severity', U32), ('ID', U32), ('pDescription', P), ('DescriptionByteLength', SZ)])
ModuleEntry = struct_type('ModuleEntry', [('dwSize', U32), ('th32ModuleID', U32), ('th32ProcessID', U32),
    ('GlblcntUsage', U32), ('ProccntUsage', U32), ('modBaseAddr', P), ('modBaseSize', U32), ('hModule', P),
    ('szModule', U16 * 256), ('szExePath', U16 * 260)])

IID_TEXT = {
    'Device': '189819f1-1db6-4b57-be54-1821339b85f7', 'Resource': '696442be-a72e-4059-bc79-5b5c98040fad',
    'Queue': '0ec870a6-5d7e-4c22-8cfc-5baae07616ed', 'Allocator': '6102dee4-af59-4b09-b999-b44d73f09b24',
    'List': '5b160d0f-ac1b-4185-8ba8-b3ae42a5a455', 'Fence': '0a753dcf-c4d8-4b91-adf6-be5a60d95a76',
    'Query': '0d9658ae-ed45-469e-a61d-970ec583cab4', 'Root': 'c54a6b66-72df-4ee8-8be5-a946a1429214',
    'PSO': '765a30f3-f624-4c6f-a828-ace948622445', 'Debug': '344488b7-6846-474b-b989-f027448245e0',
    'Info': '0742a90b-c387-483f-b946-30a7e4e61458', 'Factory': '1bc6ea02-ef36-464f-bf0c-21ca39e5168a',
    'Adapter': '29038f61-3839-4626-91fd-086879011a05', 'DXGIDevice': '54ec77fa-1377-44e6-8c32-88fd5f44c84c'}
IIDS = {k: GUID.from_buffer_copy(uuid.UUID(v).bytes_le) for k, v in IID_TEXT.items()}

# Windows C-interface vtable slots (conditional non-Windows duplicates excluded).
# Each signature includes the implicit This in method(), never inferred by ctypes.
METHODS = {
    'QueryInterface': (0, I32, (PTR(GUID), PTR(P))), 'Release': (2, U32, ()),
    'CreateCommandQueue': (8, I32, (PTR(QueueDesc), PTR(GUID), PTR(P))),
    'CreateCommandAllocator': (9, I32, (U32, PTR(GUID), PTR(P))),
    'CreateGraphicsPipelineState': (10, I32, (PTR(GraphicsPSO), PTR(GUID), PTR(P))),
    'CreateCommandList': (12, I32, (U32, U32, P, P, PTR(GUID), PTR(P))),
    'CheckFeatureSupport': (13, I32, (U32, P, U32)),
    'CreateRootSignature': (16, I32, (U32, P, SZ, PTR(GUID), PTR(P))),
    # d3d12.h explicitly declares Windows ABI as (This, RetVal, mask, count, desc).
    'GetResourceAllocationInfo': (25, P, (PTR(Allocation), U32, U32, PTR(ResourceDesc))),
    'CreateCommittedResource': (27, I32, (PTR(Heap), U32, PTR(ResourceDesc), U32, P, PTR(GUID), PTR(P))),
    'CreateFence': (36, I32, (U64, U32, PTR(GUID), PTR(P))),
    'GetDeviceRemovedReason': (37, I32, ()),
    'CreateQueryHeap': (39, I32, (PTR(QueryDesc), PTR(GUID), PTR(P))),
    'Close': (9, I32, ()), 'ResetList': (10, I32, (P, P)), 'ResetAllocator': (8, I32, ()),
    'DrawInstanced': (12, None, (U32, U32, U32, U32)),
    'CopyBufferRegion': (15, None, (P, U64, P, U64, U64)),
    'IASetPrimitiveTopology': (20, None, (U32,)), 'SetPipelineState': (25, None, (P,)),
    'ResourceBarrier': (26, None, (U32, PTR(Barrier))), 'SetGraphicsRootSignature': (30, None, (P,)),
    'SetGraphicsRootConstantBufferView': (38, None, (U32, U64)),
    'IASetVertexBuffers': (44, None, (U32, U32, PTR(VBView))), 'SOSetTargets': (45, None, (U32, U32, PTR(SOView))),
    'BeginQuery': (52, None, (P, U32, U32)), 'EndQuery': (53, None, (P, U32, U32)),
    'ResolveQueryData': (54, None, (P, U32, U32, U32, P, U64)),
    'ExecuteCommandLists': (10, None, (U32, PTR(P))), 'Signal': (14, I32, (P, U64)),
    'GetCompletedValue': (8, U64, ()), 'SetEventOnCompletion': (9, I32, (U64, P)),
    'Map': (8, I32, (U32, PTR(Range), PTR(P))), 'Unmap': (9, None, (U32, PTR(Range))),
    'GetGPUVirtualAddress': (11, U64, ()), 'EnableDebugLayer': (3, None, ()),
    'SetMessageCountLimit': (3, I32, (U64,)), 'GetMessage': (5, I32, (U64, P, PTR(SZ))),
    'GetNumStoredMessages': (8, U64, ()), 'GetNumMessagesDiscardedByMessageCountLimit': (10, U64, ()),
    'EnumAdapters1': (12, I32, (U32, PTR(P))), 'EnumWarpAdapter': (27, I32, (PTR(GUID), PTR(P))),
    'GetDesc1': (10, I32, (PTR(AdapterDesc),)), 'CheckInterfaceSupport': (9, I32, (PTR(GUID), PTR(C.c_int64))),
    'GetBufferPointer': (3, P, ()), 'GetBufferSize': (4, SZ, ()),
}


def validate_platform():
    need(sys.platform == 'win32' and sys.implementation.name == 'cpython' and C.sizeof(P) == 8
         and platform.machine().lower() in ('amd64', 'x86_64'), '64-bit x64 CPython on Windows required')
    need(C.sizeof(I32) == 4 and C.sizeof(SZ) == 8 and C.sizeof(C.c_wchar) == 2, 'Windows scalar widths')


def hr(value, name):
    if value < 0:
        raise RuntimeError(f'{name}: HRESULT 0x{value & 0xffffffff:08x}')
    return value


def method(pointer, name, *args):
    need(bool(pointer), 'null/released COM pointer: ' + name)
    slot, result, params = METHODS[name]
    address = C.cast(pointer, PTR(PTR(P))).contents[slot]
    value = CALL(result, P, *params)(address)(pointer, *args)
    return value


class Owner:
    """Own exactly one acquired COM reference. No implicit __del__ teardown."""
    def __init__(self, pointer):
        self.p = P(pointer.value if isinstance(pointer, P) else pointer)
        need(bool(self.p), 'null acquired COM pointer')

    def call(self, name, *args):
        value = method(self.p, name, *args)
        if METHODS[name][1] is I32:
            hr(value, name)
        return value

    def close(self):
        if self.p:
            pointer, self.p = self.p, P()
            method(pointer, 'Release')


def wide(array):
    return bytes(array).decode('utf-16-le').split('\0', 1)[0]


def dll_function(dll, name, result, params):
    function = getattr(dll, name)
    function.restype, function.argtypes = result, params
    return function


class Libraries:
    def __init__(self):
        validate_platform()
        # LOAD_LIBRARY_SEARCH_SYSTEM32: never load DLLs from the repro folder.
        self.d3d = C.WinDLL('d3d12.dll', winmode=0x800)
        self.dxgi = C.WinDLL('dxgi.dll', winmode=0x800)
        self.kernel = C.WinDLL('kernel32.dll', winmode=0x800, use_last_error=True)
        self.create_factory = dll_function(self.dxgi, 'CreateDXGIFactory2', I32, [U32, PTR(GUID), PTR(P)])
        self.create_device = dll_function(self.d3d, 'D3D12CreateDevice', I32, [P, U32, PTR(GUID), PTR(P)])
        self.get_debug = dll_function(self.d3d, 'D3D12GetDebugInterface', I32, [PTR(GUID), PTR(P)])
        self.serialize = dll_function(self.d3d, 'D3D12SerializeRootSignature', I32, [PTR(RootDesc), U32, PTR(P), PTR(P)])
        self.create_event = dll_function(self.kernel, 'CreateEventW', P, [P, I32, I32, C.c_wchar_p])
        self.wait = dll_function(self.kernel, 'WaitForSingleObject', U32, [P, U32])
        self.close_handle = dll_function(self.kernel, 'CloseHandle', I32, [P])
        self.snapshot = dll_function(self.kernel, 'CreateToolhelp32Snapshot', P, [U32, U32])
        self.module_first = dll_function(self.kernel, 'Module32FirstW', I32, [P, PTR(ModuleEntry)])
        self.module_next = dll_function(self.kernel, 'Module32NextW', I32, [P, PTR(ModuleEntry)])
