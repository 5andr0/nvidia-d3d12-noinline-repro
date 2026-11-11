# D3D12 noinline shader reproducer

A pure-Python host for a small vertex-shader case. Earlier direct Python baseline controls on an RTX 5080 reproduced **48 incorrect words out of 112**; WARP matched all 112 exactly. Both controls completed with the D3D12 debug layer enabled, and their full raw evidence was checked. See [REPORT.md](REPORT.md) for results and environment details.

The host calls Windows D3D12, DXGI and Win32 directly through Python's standard-library `ctypes`. It supplies the exact, normally signed [compiled shader](data/baseline.dxil) alongside the [readable HLSL](https://raw.githubusercontent.com/5andr0/nvidia-d3d12-noinline-repro/main/source/baseline.hlsl). All inputs are synthetic and generated in Python.

## Run

Requires Windows x64, 64-bit x64 CPython 3.9 or newer, and an installed D3D12 runtime/driver that accepts shader model 6.8. **No C++ or shader compilation, SDK, MSVC, DXC, pip packages, supplied EXE/DLL, game, profiler or attached monitor is required to execute the repro.**

```bat
git clone https://github.com/5andr0/nvidia-d3d12-noinline-repro.git
cd nvidia-d3d12-noinline-repro
py repro.py --all
```

GitHub's **Code > Download ZIP** also works: extract the archive and run `py repro.py --all` in that folder.

`--all` starts this same Python interpreter once for NVIDIA and once for WARP. Each child creates one device and direct queue. Missing adapters and unsupported shader capabilities are reported; there is no implicit adapter, fallback or retry. Multiple NVIDIA adapters require an explicit LUID. The default controls contain no Vulkan path.

```bat
py repro.py --vendor nvidia
py repro.py --warp
py repro.py --list
py repro.py --luid 00000000:00001234
```

`--list` explicitly creates a DXGI factory to enumerate adapters, without creating a device. The LUID above is an example; use a value from your own inventory. `--output fresh-folder` optionally chooses a fresh result session directory.

For graphics-free fixture, ABI-layout, oracle and supervision checks:

```bat
py repro.py --check-only
```

This mode does not load D3D12/DXGI or enumerate hardware. The normal run verifies all pinned bytes before graphics access. A missing or modified shader makes the run ineligible; nothing downloads, recompiles or relaxes a pin.

## Optional paired cases

The default `--case baseline` uses the unchanged historical SDK shader. Optional cases are supplied as normally signed DXIL; running them requires no compiler. These are measured RTX 5080 results with the debug layer enabled:

| Case | Helper form | Compiler | NVIDIA wrong / 112 | WARP wrong / 112 |
|---|---|---|---:|---:|
| `baseline` (default) | Scalar return | Stock SDK DXC | 48 | 0 |
| `scalar-amended` | Identical scalar-return HLSL | Amended DXC | 48 | 0 |
| `out-amended` | Void with scalar `out` result | Same amended DXC | 0 | 0 |
| `array-stock` | Void with typed `inout` operand array | Same stock SDK DXC as baseline | 0 | 0 |

The stock candidate initializes an array with the actual operands, performs the same precise operation inside a noinline helper, and overwrites its first element with the result. Read the [plain candidate HLSL](https://raw.githubusercontent.com/5andr0/nvidia-d3d12-noinline-repro/main/source/array-inout.hlsl). No operation is removed or reordered, and no precision flag is relaxed. The `array-stock` result needs no custom compiler.

Run each selected case separately:

```bat
py repro.py --case baseline --all
py repro.py --case array-stock --all
py repro.py --case scalar-amended --all
py repro.py --case out-amended --all
```

Each invocation selects NVIDIA and WARP only, with one draw per adapter and no retries. `--vendor amd` remains an explicit optional control, for example `py repro.py --case out-amended --vendor amd`. All other selectors also accept `--case`. There is no automatic comparison loop.

All cases retain POS/WEIGHT/INDEX inputs, SV_Position/ROW0..3/RAW0..1 outputs, 20 noinline helpers, 37 live helper calls, 12 precise dots, input values, operation order and oracle. The candidate sources change helper operand/result transport. CPU checks establish source inversion, matching graphics signature/PSV bytes and all 82 dependency edges. Hardware checks compare every output bit. Neither establishes a driver-internal call-ABI explanation or qualifies all shaders, compiler versions or rendering performance. [Case hashes and compiler provenance](evidence/cases.json) identify the supplied bytes.

For each case, `py repro.py --case CASE --check-only` runs the graphics-free checks. The selected case, source and shader identities are retained in session/capture `case.json`, input identities, child results, supervision and summaries. The historical `BASELINE.*` raw-output filenames remain in use for every case; `case.json` identifies their shader.

## Results and bounds

Keep the complete unique folder under `results/`, including `summary.json`, separate child stdout/stderr, raw inputs/readbacks, the 600-byte audit, full 112-word CSV/JSON, adapter/driver metadata and loaded-module hashes. A child must exit cleanly and pass all raw/debug gates before any numerical interpretation. The parent independently verifies the retained evidence.

Classifications are `CORRECT`, `KNOWN_BAD`, `OTHER_FINITE_MISMATCH`, `UNSUPPORTED` and `INCOMPLETE`. `KNOWN_BAD` means an exact match of all 448 historical output bytes. The comparison fixture never supplies GPU output. Parent exit 0 means all selections are correct, 2 means at least one valid numerical mismatch, and 1 means an incomplete, unsupported or failed selection. A child's exit 0 indicates complete execution and can still accompany incorrect numbers.

Each selection has a 60-second parent deadline, a five-second kill/drain bound, a 64 MiB output cap and no retries. Safety or drainage failure stops subsequent selections. The nine explicit GPU buffer allocation requests have a cumulative 128 MiB cap checked against `GetResourceAllocationInfo` before creation. Each submission uses a native ten-second fence wait. Failure with GPU work pending terminates the child before COM/resource teardown.

The optional Windows debug layer is used when already available; availability is disclosed. ERROR/CORRUPTION messages, discarded messages or incomplete debug capture invalidate numerical interpretation. Nothing installs the layer or changes system settings.

## Route

Every `vs_6_8` case uses root CBVs b0/b1/b2, the original POS/WEIGHT/INDEX layout (offsets 0/16/32, stride 48), a 192-byte four-vertex buffer, and a 24,576-byte palette containing literal floats 1 through 6144. Full GPU input readbacks must match before PSO creation.

Two fenced submissions perform input verification and one four-vertex `DrawInstanced` point-list draw. Stream output captures SV_Position, ROW0-3 and RAW0-1 at stride 112, with no rasterization, window or swapchain. The audit checks two 64-byte guards, the 448-byte payload and filled/written/needed counts 448/4/4. All 112 words must be finite. An independent integer oracle compares exact binary32 bits; all exercised arithmetic intermediates are at most 5350.

[ABI.md](ABI.md) documents binding provenance and ownership. CPU verification does not establish GPU behavior or fault ownership.

## Optional shader compilation

Compilation is only for readers investigating the sources. It is **not part of running any case**. The original baseline remains byte-preserved: 9796 bytes, SHA256 `97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208`. Its HLSL SHA256 is `0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb`.

The historical baseline was compiled with stock DXC 1.8.2502.11 in Windows SDK 10.0.26100.0. A separate recompile can use:

```bat
"%ProgramFiles(x86)%\Windows Kits\10\bin\10.0.26100.0\x64\dxc.exe" -E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz -Fo baseline.recompiled.dxil source\baseline.hlsl
```

The `array-stock` candidate uses that same unmodified stock SDK compiler and normal validation/signing:

```bat
"%ProgramFiles(x86)%\Windows Kits\10\bin\10.0.26100.0\x64\dxc.exe" -E main -T vs_6_8 -HV 2018 -Ges -denorm ftz -Fo array-stock.recompiled.dxil source\array-inout.hlsl
```

Its supplied shader is 15724 bytes, SHA256 `1fbed79006488999391766c4471ad9dfe7ca2b38f4b0e813f2619d5443e80572`. Stock `dxcompiler.dll` SHA256: `78b5e21a91707b4a567ef281a519c52a45b709561202f54c5ad79c5a315847ed`.

Both amended cases were compiled with the **same unreleased, source-built amended DXC**, associated with [Microsoft DXC PR #9114](https://github.com/microsoft/DirectXShaderCompiler/pull/9114), [source commit da86a8b0](https://github.com/5andr0/DirectXShaderCompiler/commit/da86a8b0b8e8d4de8f34455fdf6566167c555643). This is not a stock or released SDK compiler. Its `dxcompiler.dll` SHA256 is `22ecda27e07e0770ff89f883f798614430cff2da7a243efea6cb8055226783c1`. The build's creator string predates the final source commit amendment; the DLL hash identifies the actual qualified build (details in [cases.json](evidence/cases.json)).

To compile the pair optionally, point `DXC` at that build's `dxc.exe` and explicitly select the official Windows SDK validator. The observed loaded `dxil.dll` SHA256 was `77e039c905030a641e53658a008b74e90635a5ea9b6b79eabd0f2003bdfca59a`:

```bat
set "DXC=C:\path\to\amended-dxc\dxc.exe"
set "DXC_DXIL_DLL_PATH=%ProgramFiles(x86)%\Windows Kits\10\bin\10.0.26100.0\x64\dxil.dll"
"%DXC%" source\baseline.hlsl -E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz -Fo scalar-amended.recompiled.dxil
"%DXC%" source\out-result.hlsl -E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz -Fo out-amended.recompiled.dxil
```

The supplied pair used normal validation/signing, with no `-Vd`, assembly/IR modification or manual signing. Actual compiler/validator DLL loads were observed during CPU compilation; full reflection and PSV checks were retained. No compiler, validator DLL, native host executable or SDK tree is bundled. Compiler versions may produce different bytes; keep experimental outputs separate from the pinned supplied cases.
