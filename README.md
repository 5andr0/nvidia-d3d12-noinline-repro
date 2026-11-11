# D3D12 noinline shader reproducer

A pure-Python host for a small vertex-shader case. On an RTX 5080, this host reproduces **48 incorrect words out of 112**; the WARP control matches all 112 exactly. Both controls completed with the D3D12 debug layer enabled, and their full raw evidence was checked. See [REPORT.md](REPORT.md) for results and environment details.

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

## Results and bounds

Keep the complete unique folder under `results/`, including `summary.json`, separate child stdout/stderr, raw inputs/readbacks, the 600-byte audit, full 112-word CSV/JSON, adapter/driver metadata and loaded-module hashes. A child must exit cleanly and pass all raw/debug gates before any numerical interpretation. The parent independently verifies the retained evidence.

Classifications are `CORRECT`, `KNOWN_BAD`, `OTHER_FINITE_MISMATCH`, `UNSUPPORTED` and `INCOMPLETE`. `KNOWN_BAD` means an exact match of all 448 historical output bytes. The comparison fixture never supplies GPU output. Parent exit 0 means all selections are correct, 2 means at least one valid numerical mismatch, and 1 means an incomplete, unsupported or failed selection. A child's exit 0 indicates complete execution and can still accompany incorrect numbers.

Each selection has a 60-second parent deadline, a five-second kill/drain bound, a 64 MiB output cap and no retries. Safety or drainage failure stops subsequent selections. The nine explicit GPU buffer allocation requests have a cumulative 128 MiB cap checked against `GetResourceAllocationInfo` before creation. Each submission uses a native ten-second fence wait. Failure with GPU work pending terminates the child before COM/resource teardown.

The optional Windows debug layer is used when already available; availability is disclosed. ERROR/CORRUPTION messages, discarded messages or incomplete debug capture invalidate numerical interpretation. Nothing installs the layer or changes system settings.

## Route

The unchanged `vs_6_8` shader uses root CBVs b0/b1/b2, the original POS/WEIGHT/INDEX layout (offsets 0/16/32, stride 48), a 192-byte four-vertex buffer, and a 24,576-byte palette containing literal floats 1 through 6144. Full GPU input readbacks must match before PSO creation.

Two fenced submissions perform input verification and one four-vertex `DrawInstanced` point-list draw. Stream output captures SV_Position, ROW0-3 and RAW0-1 at stride 112, with no rasterization, window or swapchain. The audit checks two 64-byte guards, the 448-byte payload and filled/written/needed counts 448/4/4. All 112 words must be finite. An independent integer oracle compares exact binary32 bits; all exercised arithmetic intermediates are at most 5350.

[ABI.md](ABI.md) documents binding provenance and ownership. CPU verification does not establish GPU behavior or fault ownership.

## Optional shader compilation

Compilation is only for readers investigating the source. It is **not part of running the repro**. Use a Microsoft-provided DXC and its normal validator, for example the stock DXC 1.8.2502.11 in Windows SDK 10.0.26100.0:

```bat
"%ProgramFiles(x86)%\Windows Kits\10\bin\10.0.26100.0\x64\dxc.exe" -E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz -Fo baseline.recompiled.dxil source\baseline.hlsl
```

The supplied shader is 9796 bytes, SHA256 `97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208`. The byte-preserved HLSL SHA256 is `0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb`. Compiler versions may produce different output; keep intentional variants separate. The baseline run always requires the supplied exact bytes and normal D3D12 validation.
