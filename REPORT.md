# [D3D12] Incorrect vertex shader values with noinline helpers on NVIDIA; WARP control correct

A small, standalone D3D12 vertex shader produces repeatable incorrect values on NVIDIA hardware. The same compiled shader and synthetic inputs produce the exact expected values on AMD integrated graphics and Microsoft WARP. Please investigate the NVIDIA compilation/execution path; the precise internal cause has not been established.

## Direct Python results

The direct Python/ctypes host was tested on Windows 11 build26200.9711 with 64-bit CPython3.13.15:

| Control | Wrong words /112 | Driver | Result |
|---|---:|---|---|
| NVIDIA GeForce RTX5080 |48|DXGI32.0.16.2114 / GeForce621.14|Exact known-bad448-byte payload|
| Microsoft WARP |0|10.0.26100.9711|Exact independent integer oracle|

Each control used one four-vertex draw and two fenced submissions. Both children exited0 and drained; normal D3D12 debug capture was enabled and contained no ERROR/CORRUPTION messages. Three warning1328 diagnostics per control report buffers effectively starting in COMMON. Full inputs/readbacks, guards, counters, all112 words, CSV/JSON agreement, allocation ledgers and actual runtime/adapter identities were checked independently of the host's result classifier. The host and shader were unchanged between controls.

The later default `--all` selection change simply limits the command to NVIDIA plus WARP; the individual graphics and supervision paths are unchanged and CPU-tested. No Vulkan implementation or Vulkan test is included. Separate earlier Vulkan precision-fixture results are not a measurement of this exact112-word D3D12 case.

## Historical C++ host results

| Test | Wrong 32-bit words / 112 | Debug layer | Evidence |
|---|---:|---|---|
| RTX 5080, driver 32.0.16.2114 |48|Enabled|Full raw inputs, readbacks and outputs inspected|
| NVIDIA on a second PC, described as RTX 3090 |48|Enabled|Reporter-provided console summary; adapter/driver metadata pending|
| AMD integrated graphics on the second PC |0|Enabled|Reporter-provided console summary|
| WARP on the second PC |0|Enabled|Reporter-provided console summary|
| WARP on the RTX 5080 host |0|Enabled|Full raw inputs, readbacks and outputs inspected|

Every reported process exited 0 with `numeric_interpretation=true`. NVIDIA's `KNOWN_BAD` classification reports an exact match with the earlier 448-byte failure payload, not merely the same mismatch count. The second-PC raw result folders have not yet been independently inspected. Its exact NVIDIA/AMD driver and Windows versions should be added when available.

The RTX 5080 host is Windows 11 build 26200.9711 (25H2). The first vertex's expected output is `(2700,2980,3260,1)`; NVIDIA produces `(2700,3820,4100,1)`. Saved first-bone Y/Z rows match the fourth bone's rows instead. Execution completes normally: this is incorrect output, not a compilation failure or device crash.

## Pure-Python reproducer

Repository: **https://github.com/5andr0/nvidia-d3d12-noinline-repro**.

The repository contains the [plain HLSL shader](https://raw.githubusercontent.com/5andr0/nvidia-d3d12-noinline-repro/main/source/baseline.hlsl), its exact normally signed [compiled DXIL](https://github.com/5andr0/nvidia-d3d12-noinline-repro/blob/main/data/baseline.dxil), a direct Python/ctypes D3D12 host, Python synthetic fixture/oracle generation and historical text CSVs. There is no supplied native host executable or DLL.

**The historical table records the original C++ host; the direct Python controls are recorded separately above.** The second PC was described as an RTX 3090 system with a 9950X3D; exact raw adapter, driver and OS metadata remain pending.

Execution requires Windows x64, 64-bit x64 CPython 3.9 or newer, and an installed D3D12 runtime/driver supporting shader model 6.8. No SDK, MSVC, DXC, pip package, C++ compilation or shader compilation is required to run it.

```bat
git clone https://github.com/5andr0/nvidia-d3d12-noinline-repro.git
cd nvidia-d3d12-noinline-repro
py repro.py --all
```

The Python parent starts the same Python interpreter separately for NVIDIA and WARP. Each child calls the Windows APIs directly through `ctypes`. GitHub's **Code > Download ZIP** also works. Single selections use `--vendor nvidia` or `--warp`; `--check-only` runs CPU checks without loading graphics DLLs or enumerating hardware.

Keep the complete results session, including `summary.json`. Parent exit 0 means every selection matches the oracle, 2 means a valid numerical mismatch, and 1 means an incomplete, unsupported or failed selection. A child must exit 0, retain complete raw evidence and pass the debug gates before its numbers are interpreted. Normal debug-layer availability is disclosed; ERROR/CORRUPTION messages invalidate interpretation.

Shader compilation instructions are an **optional** separate section in the [README](https://github.com/5andr0/nvidia-d3d12-noinline-repro#optional-shader-compilation). The exact supplied shader is `vs_6_8`, compiled normally with `-E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz`. It contains 20 noinline scalar-return helpers, 37 live calls and 12 precise dots. This route bypasses wgpu, Naga and Iridia entirely.

The supplied shader is 9796 bytes, SHA256 `97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208`. A hash mismatch makes the baseline ineligible before graphics access. No validator setting, assertion or test is disabled, and no shader is regenerated during execution.

## Correctness checks and evidence boundary

The direct Python controls preserve these checks. All exercised arithmetic intermediates are positive integers no greater than 5350, exactly representable in binary32. An independent integer oracle checks all 112 output words without tolerance. Full vertex/constant-buffer readbacks are checked before PSO creation. The raw 600-byte stream-output audit retains two 64-byte guards, the 448-byte payload and filled/written/needed counts 448/4/4. Normal debug-layer capture found no ERROR/CORRUPTION messages in the independently inspected current-host controls. The result folders retain complete per-word CSV/JSON comparisons and adapter/runtime identities.

The source archive includes all expected and historical observed values as text CSVs. A separate out-result source form has produced correct results on this host, but it changes the compiled form and does not isolate an ABI fault. No production workaround or native-instruction chronology is claimed.

Please reproduce the attached source on NVIDIA hardware and investigate preservation of the indexed row values across the non-inlined helper calls. The additional NVIDIA/AMD/WARP comparison strengthens the NVIDIA-specific diagnosis, but does not by itself conclusively assign fault ownership.
