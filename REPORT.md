# D3D12: incorrect vertex shader results with noinline scalar-return helpers on NVIDIA

A standalone `vs_6_8` shader produces repeatable incorrect values on NVIDIA. The same compiled shader and inputs match the exact oracle on WARP. A source-equivalent helper prototype change also produces correct results on NVIDIA with the same stock DXC.

- [Reproducer and harness](https://github.com/5andr0/nvidia-d3d12-noinline-repro)
- [Failing baseline HLSL](https://raw.githubusercontent.com/5andr0/nvidia-d3d12-noinline-repro/main/source/baseline.hlsl)
- [Passing inout-array HLSL](https://raw.githubusercontent.com/5andr0/nvidia-d3d12-noinline-repro/main/source/array-inout.hlsl)
- [Measured results and per-word evidence](https://github.com/5andr0/nvidia-d3d12-noinline-repro/blob/main/evidence/comparison-results.json)

## Environment and failure

RTX 5080, NVIDIA driver **32.0.16.2114 / GeForce 621.14**, Windows 11 **26200.9711**. Stock compiler: Windows SDK **10.0.26100.0**, DXC **1.8.2502.11**. Compilation and validation/signing use the unmodified SDK tools.

The shader performs indexed palette loads and weighted dot products through **20 noinline helpers, 37 live calls and 12 precise dots**. All inputs are synthetic. The intended arithmetic intermediates are positive integers no greater than 5350, exactly representable in binary32. An independent integer oracle compares all **112 output words** without tolerance.

NVIDIA returns **48/112 incorrect words**. For the first vertex, expected `SV_Position` is `(2700, 2980, 3260, 1)`; observed output is `(2700, 3820, 4100, 1)`. Captured first-bone Y/Z row values equal the fourth bone's rows. The complete 448-byte output matches the retained failure payload.

Both NVIDIA and WARP runs complete normally with the debug layer enabled and no ERROR/CORRUPTION messages. Full VB/CB GPU readbacks match before PSO creation. Stream-output guards, filled/written/needed counters and every output word are retained and checked. This reproducer calls D3D12 directly, independently of wgpu, Naga or Iridia.

## Controlled prototype comparison

Fresh measurements on the same RTX 5080 host; one draw per adapter/case, no retries:

| Helper form | Compiler | NVIDIA wrong / 112 | WARP wrong / 112 |
|---|---|---:|---:|
| Scalar return, baseline | Stock SDK DXC | 48 | 0 |
| Identical scalar-return source | Amended DXC | 48 | 0 |
| Void with scalar `out` result | Same amended DXC | 0 | 0 |
| Void with typed `inout` operand array | Same stock SDK DXC as baseline | 0 | 0 |

The passing stock form initializes a local array with the actual operands, performs the original operation inside a noinline helper, and overwrites element zero:

```hlsl
[noinline] void multiply(inout float operands[2]) {
    precise float result = operands[0] * operands[1];
    operands[0] = result;
}
float operands[2] = { left, right };
multiply(operands);
float result = operands[0];
```

The full candidate retains ordered arithmetic, precision boundaries, all 20 helpers/37 calls/12 dots, identical graphics signatures and all **82 input-to-output dependency edges**. No extra floating-point arithmetic or fabricated live operands are introduced. The amended-compiler pair is an additional control using the unreleased dependency-analysis fix from DXC PR #9114; the passing stock-array case does not require it.

A second-host report showed RTX 3090 **48/112**, AMD integrated graphics **0/112**, and WARP **0/112**, with clean exits and debug enabled. That host's raw folders and exact driver/OS metadata have not yet been independently reviewed.

## Run and compile

The Python/ctypes harness submits one four-vertex point-list draw with stream output, without rasterization or a swapchain. Normally signed DXIL is supplied alongside HLSL. Running requires Windows x64, 64-bit CPython 3.9+ and SM6.8 support; it does not invoke a compiler.

```bat
py repro.py --all
py repro.py --case array-stock --all
```

`--all` selects NVIDIA and WARP. Individual adapters can be selected with `--vendor nvidia`, `--warp` or an explicit `--luid`. Results include adapter/runtime identities, source and shader hashes, full raw input/output checks and `summary.json`.

For source investigation, compile separately with the stock SDK compiler:

```bat
set "DXC=%ProgramFiles(x86)%\Windows Kits\10\bin\10.0.26100.0\x64\dxc.exe"
"%DXC%" source\baseline.hlsl -E main -T vs_6_8 -HV 2018 -Ges -denorm ftz -Fo baseline.recompiled.dxil
"%DXC%" source\array-inout.hlsl -E main -T vs_6_8 -HV 2018 -Ges -denorm ftz -Fo array-stock.recompiled.dxil
```

Exact supplied shader/compiler hashes and compile provenance are in `evidence/cases.json`. No validation bypass or IR/metadata modification was used.

Please investigate preservation of the indexed row values across the original non-inlined scalar-return calls. The prototype comparison narrows the trigger and supplies a working source-level alternative for this case; it does not establish the driver's internal failure mechanism or general performance/compatibility.
