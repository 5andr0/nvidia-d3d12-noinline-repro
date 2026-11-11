# [D3D12] Incorrect vertex shader values with noinline helpers on NVIDIA; AMD and WARP correct

A small, standalone D3D12 vertex shader produces repeatable incorrect values on NVIDIA hardware. The same compiled shader and synthetic inputs produce the exact expected values on AMD integrated graphics and Microsoft WARP. Please investigate the NVIDIA compilation/execution path; the precise internal cause has not been established.

## Results

| Test | Wrong 32-bit words /112 | Debug layer | Evidence |
|---|---:|---|---|
| RTX5080, driver32.0.16.2114 |48|Enabled|Full raw inputs, readbacks and outputs inspected|
| NVIDIA on a second PC, described as RTX3090 |48|Enabled|Reporter-provided console summary; adapter/driver metadata pending|
| AMD integrated graphics on the second PC |0|Enabled|Reporter-provided console summary|
| WARP on the second PC |0|Enabled|Reporter-provided console summary|
| WARP on the RTX5080 host |0|Enabled|Full raw inputs, readbacks and outputs inspected|

Every reported process exited0 with `numeric_interpretation=true`. NVIDIA's `KNOWN_BAD` classification reports an exact match with the earlier448-byte failure payload, not merely the same mismatch count. The second-PC raw result folders have not yet been independently inspected. Its exact NVIDIA/AMD driver and Windows versions should be added when available.

The RTX5080 host is Windows11 build26200.9711 (25H2). The first vertex's expected output is `(2700,2980,3260,1)`; NVIDIA produces `(2700,3820,4100,1)`. Saved first-bone Y/Z rows match the fourth bone's rows instead. Execution completes normally: this is incorrect output, not a compilation failure or device crash.

## Source-only reproducer

Source-only reproducer: **https://github.com/5andr0/nvidia-d3d12-noinline-repro**.

The repository contains readable [HLSL](https://github.com/5andr0/nvidia-d3d12-noinline-repro/blob/main/source/baseline.hlsl), the small native C++ harness, synthetic fixture generation, build scripts and text result CSVs. It contains no EXE, DLL, compiled shader/DXIL, object/debug files, game assets or SDK files.

With Windows x64, Python3.9+, Visual Studio C++ Build Tools and Windows SDK10.0.26100.0 (stock DXC1.8.2502.11):

```bat
git clone https://github.com/5andr0/nvidia-d3d12-noinline-repro.git
cd nvidia-d3d12-noinline-repro
py repro.py --all
```

The Python standard-library wrapper finds the installed Microsoft tools, builds the shader/program locally and collects independent NVIDIA, AMD and WARP results. No pip packages, downloaded executables, game or display connection are needed. Individual selections use `--vendor nvidia`, `--vendor amd` or `--warp`; `--build-only` compiles and checks CPU data without graphics access. A source ZIP downloaded from GitHub works as well.

The source-only build recipe was verified: it compiles and passes graphics-free CPU checks, and regenerates the exact shader and all synthetic input/reference bytes used in the reported test. No graphics test runs as part of the build.

The shader is `vs_6_8`, compiled normally with `-E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz`. It contains20 noinline scalar-return helpers,37 live calls and12 precise dots. It reads a synthetic palette using four runtime indices, computes weighted positions, and exports saved rows and intermediate results. The reproduction bypasses wgpu, Naga and Iridia entirely.

The compiled shader is validated/signed normally. Expected shader SHA256: `97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208`. The harness refuses a different shader rather than silently substituting one. No validator setting, assertion or test is disabled.

## Correctness checks

All exercised arithmetic intermediates are positive integers no greater than5350, exactly representable in binary32. An independent integer oracle checks all112 output words without tolerance. Full vertex/constant-buffer readbacks are checked before PSO creation. The raw600-byte stream-output audit retains two64-byte guards, the448-byte payload and filled/written/needed counts448/4/4. Normal debug-layer capture found no ERROR/CORRUPTION messages in the independently inspected current-host controls. The result folders retain complete per-word CSV/JSON comparisons and adapter/runtime identities.

The source archive includes all expected and historical observed values as text CSVs. A separate out-result source form has produced correct results on this host, but it changes the compiled form and does not isolate an ABI fault. No production workaround or native-instruction chronology is claimed.

Please reproduce the attached source on NVIDIA hardware and investigate preservation of the indexed row values across the non-inlined helper calls. The additional NVIDIA/AMD/WARP comparison strengthens the NVIDIA-specific diagnosis, but does not by itself conclusively assign fault ownership.
