# Windows ABI and provenance

`winabi.py` contains authored, minimal declarations for the documented Windows x64 COM interfaces used by this repro. No SDK header tree or native shim is included. Importing this module declares types only; the child explicitly loads system D3D12/DXGI DLLs after input verification. CPython, pointers and `SIZE_T` must be 64-bit; `HRESULT`, Windows enums, `UINT` and `BOOL` are 32-bit. UTF-16 arrays use explicit 16-bit elements.

The development reference is installed Windows SDK **10.0.26100.0**, particularly `um/d3d12.h`, `um/d3d12sdklayers.h`, `um/d3dcommon.h`, `shared/dxgi.h`, `shared/dxgi1_4.h` and `um/TlHelp32.h`. These are development evidence, not execution dependencies. Relevant public contracts:

- [Microsoft DirectX-Headers: d3d12.h](https://github.com/microsoft/DirectX-Headers/blob/main/include/directx/d3d12.h)
- [Microsoft D3D12 interfaces](https://learn.microsoft.com/en-us/windows/win32/direct3d12/direct3d-12-interfaces)
- [Microsoft DXGI interfaces](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/d3d10-graphics-reference-dxgi-interfaces)
- [Microsoft x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention)
- [Python ctypes, WinDLL and WINFUNCTYPE](https://docs.python.org/3/library/ctypes.html)
- [Root signature serialization](https://learn.microsoft.com/en-us/windows/win32/api/d3d12/nf-d3d12-d3d12serializerootsignature)

Each used COM method has an explicit vtable slot, return type and argument tuple in `METHODS`. `WINFUNCTYPE` receives the explicit `This` pointer. HRESULT failure is checked using a signed 32-bit result. Successful acquisitions and `QueryInterface` each transfer one owned reference to `Owner`; `close()` releases it exactly once. There is no destructor-driven release. CPU-owned arrays, shader bytes and descriptions stay alive throughout their synchronous calls; GPU resources stay alive until the relevant fence completes.

## Structure returns

Do not declare `GetResourceAllocationInfo` as an ordinary function returning a ctypes structure. The installed SDK's Windows C-interface declaration explicitly takes `(This, RetVal, visibleMask, numResourceDescs, pResourceDescs)` and returns the result pointer. Its vtable slot is 25. The binding uses that declaration and checks returned-pointer identity before using the allocation size and alignment. Conditional non-Windows alternatives in the generated header do not create additional Windows vtable slots.

A separate, private, graphics-free development probe checked every declared structure's size, alignment and field offsets against the installed SDK, plus every used vtable slot. A genuine C++ virtual member returning the same 16-byte allocation structure confirmed the lowered parameter order and returned pointer identity. The probe imported only Kernel32 and is neither shipped nor required to run this project. Python CPU tests additionally exercise the vtable call through a local callback and check reference ownership. These are CPU ABI checks, not GPU qualification.

Selected x64 layout checks:

| Type | Size | Key offsets |
|---|---:|---|
| D3D12_RESOURCE_DESC | 56 | Alignment 8, Width 16, SampleDesc 36, Flags 48 |
| D3D12_RESOURCE_ALLOCATION_INFO | 16 | SizeInBytes 0, Alignment 8 |
| D3D12_ROOT_PARAMETER | 32 | union 8, ShaderVisibility 24 |
| D3D12_GRAPHICS_PIPELINE_STATE_DESC | 656 | StreamOutput 88, BlendState 120, InputLayout 552, CachedPSO 632 |
| D3D12_RESOURCE_BARRIER | 32 | transition union 8 |
| DXGI_ADAPTER_DESC1 | 312 | AdapterLuid 296, Flags 304 |

## Lifetimes and execution

The direct queue receives two submissions. Allocator reset follows the first completed fence. A native event wait bounds each fence to ten seconds; a pending-work failure calls `os._exit(125)` before releasing any COM object. The separate Python parent imposes the outer deadline without relying on the child's GIL or stdio locks. No in-process Python watchdog claims to preempt native calls.

The nine committed-buffer requests are checked using actual allocation information before creation, with a cumulative 128 MiB cap. Copy bounds, heap types and resource states are tracked in Python. Root signature serialization uses the system D3D12 function; it is not shader compilation. The supplied DXIL passes through the installed D3D12 runtime's normal validation path.

CPU test success establishes fixture identities, arithmetic, layouts and the tested failure handling. Independent source review and the direct Python NVIDIA/WARP controls are complete for the documented Windows x64 environment; they do not establish correctness on other architectures or full application parity.
