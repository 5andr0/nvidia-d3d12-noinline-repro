# D3D12 noinline shader reproducer

A small, source-only reproducer for incorrect vertex shader values observed on NVIDIA hardware. AMD integrated graphics and Windows WARP have produced the exact expected result. See [the report](REPORT.md) for evidence and remaining environment details.

Read the [plain HLSL shader](https://raw.githubusercontent.com/5andr0/nvidia-d3d12-noinline-repro/main/source/baseline.hlsl) or [browse it on GitHub](source/baseline.hlsl). All input data is synthetic and generated locally. The repository contains no executable, DLL, compiled shader, game data or SDK files.

## Run

Requires Windows x64, Python 3.9 or newer, Visual Studio C++ Build Tools and Windows SDK 10.0.26100.0 with its stock DXC 1.8.2502.11. No Python packages, profiler, game or attached monitor on the selected adapter are needed.

```bat
git clone https://github.com/5andr0/nvidia-d3d12-noinline-repro.git
cd nvidia-d3d12-noinline-repro
py repro.py --all
```

Python locates the installed Microsoft tools, compiles the HLSL and C++ locally, checks the exact shader, then runs NVIDIA, AMD and WARP in separate processes, once each. It prints the results and saves the full evidence under `results/`. Missing adapters and unsupported shader model 6.8 are reported separately.

Alternatively, use **Code → Download ZIP**, extract the source, open a terminal in the extracted directory and run `py repro.py --all`.

For one adapter only:

```bat
py repro.py --vendor nvidia
py repro.py --vendor amd
py repro.py --warp
```

To check the build without any graphics/device access:

```bat
py repro.py --build-only
```

Alternatively, use an x64 Visual Studio Developer Command Prompt: run `Build.cmd`, then `Run-Tests.cmd`. For several adapters from one vendor, use the locally built `diagnostic.exe --list` and `diagnostic.exe --luid HIGH:LOW --output fresh-output-directory`.

The Python wrapper exits 0 when every selected result matches the oracle, 2 when a valid numerical mismatch is observed, or 1 when a selection is incomplete, unsupported or fails setup. The native process's exit 0 means complete execution; its result can still be numerically wrong. Inspect `summary.json` and keep the entire results directory.

## What it tests

One four-vertex point-list draw per selection, using a vertex shader and stream output. There is no rasterization, window, swapchain or presentation. Four distinct runtime bone indices select rows from a synthetic palette. Twenty noinline helpers compute the original precise operations; 37 calls and 12 dots survive stock compilation.

All 112 output words are checked against an independent integer oracle. Every exercised intermediate is at most 5350 and exactly representable in binary32. Full input readbacks, stream-output guards/counts, output words, debug-layer availability, adapter and loaded-module identities are retained. A run has one device/direct queue and one draw, with bounded waits and explicit buffer allocations.

The expected baseline shader hash is pinned to the measured case. The HLSL is intentionally byte-preserved, including line endings. A different compiler output is refused; keep compiler details when investigating a different version rather than treating that as the same baseline. All source and build flags are available for an intentional variant.

No binaries are downloaded or supplied. The developer's installed MSVC, Windows SDK DXC and normal validator perform the build. Output memory and reference fixtures are initialized; the historical bad fixture is comparison data only and never drives shader output. The source-only build has been checked to regenerate the exact measured shader and all synthetic fixtures. No production workaround or precise internal fault attribution is claimed.
