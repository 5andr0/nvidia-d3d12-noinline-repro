"""Build the source-only reproducer with installed Microsoft tools, then run it."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
SHADER_SHA256 = "97504fa19268bf6086e15cf7944f54bb59c92647f743a1403226214253515208"
HLSL_SHA256 = "0f1a6f974cf765f9bc54553808d693437e5a3825232e49633d954585c8563bcb"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_environment() -> dict[str, str]:
    env = dict(os.environ)
    existing = shutil.which("cl.exe")
    if existing and (env.get("VSCMD_ARG_TGT_ARCH") == "x64" or Path(existing).parent.name.lower() == "x64"):
        return env
    pf = Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    vswhere = pf / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not vswhere.is_file():
        raise RuntimeError("Install Visual Studio C++ Build Tools, or use an x64 Developer Command Prompt.")
    probe = subprocess.run(
        [str(vswhere), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        check=True, capture_output=True, text=True, timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    installation = Path(probe.stdout.strip())
    versions = list((installation / "VC/Tools/MSVC").glob("*"))
    versions = [p for p in versions if (p / "bin/Hostx64/x64/cl.exe").is_file()]
    if not versions:
        raise RuntimeError("No installed x64 MSVC compiler was found.")
    msvc = max(versions, key=lambda p: tuple(int(x) for x in p.name.split(".")))
    sdk = pf / "Windows Kits/10"
    includes = [msvc / "include", *(sdk / "Include/10.0.26100.0" / n for n in ("ucrt", "shared", "um", "winrt"))]
    libraries = [msvc / "lib/x64", sdk / "Lib/10.0.26100.0/ucrt/x64", sdk / "Lib/10.0.26100.0/um/x64"]
    if not all(p.is_dir() for p in includes + libraries):
        raise RuntimeError("Install the x64 C++ tools and Windows SDK10.0.26100.0.")
    env.update(INCLUDE=";".join(map(str, includes)), LIB=";".join(map(str, libraries)))
    env["PATH"] = str(msvc / "bin/Hostx64/x64") + os.pathsep + env.get("PATH", "")
    return env


def build() -> None:
    if sha256(ROOT / "source/baseline.hlsl") != HLSL_SHA256:
        raise RuntimeError("The baseline HLSL differs from the measured source. Restore its exact bytes before the baseline test.")
    env = build_environment()
    system = Path(env.get("SystemRoot", r"C:\Windows")) / "System32"
    print("Building from source using installed MSVC and Windows SDK DXC...", flush=True)
    logpath = ROOT / "build/build.log"
    logpath.parent.mkdir(exist_ok=True)
    with logpath.open("wb") as log:
        process = subprocess.Popen([str(system / "cmd.exe"), "/d", "/c", str(ROOT / "Build.cmd")],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = process.wait(timeout=180)
        except BaseException:
            if process.poll() is None:
                subprocess.run([str(system / "taskkill.exe"), "/PID", str(process.pid), "/T", "/F"],
                               stdout=log, stderr=log, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=5)
            raise
    if code:
        print(logpath.read_text(errors="replace"), file=sys.stderr)
        raise RuntimeError(f"Build failed (exit{code}); see {logpath}")
    if sha256(ROOT / "data/baseline.dxil") != SHADER_SHA256:
        raise RuntimeError("This SDK emitted a different shader. Keep build.log and compiler details; do not edit the pin or disable validation.")
    print("Build and CPU checks passed; exact measured shader reproduced.", flush=True)


def run_once(label: str, selector: list[str], session: Path) -> dict:
    output = session / label
    stdout = session / (label + ".stdout.log")
    stderr = session / (label + ".stderr.log")
    argv = [str(ROOT / "diagnostic.exe"), *selector, "--output", str(output)]
    started = time.monotonic()
    reason = None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while process.poll() is None:
                size = stdout.stat().st_size + stderr.stat().st_size
                if output.exists():
                    size += sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
                if time.monotonic() - started > 60:
                    reason = "60-second deadline"
                    break
                if size > 64 * 1024**2:
                    reason = "64MiB output limit"
                    break
                time.sleep(0.05)
        finally:
            # The reviewed native diagnostic starts no child processes.
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    result = None
    if (output / "result.json").is_file():
        try:
            result = json.loads((output / "result.json").read_text())
        except (OSError, ValueError):
            pass
    numeric = bool(reason is None and process.returncode == 0 and result
                   and result.get("numeric_interpretation") is True)
    record = dict(selector=selector, exit=process.returncode, supervision_error=reason,
                  numeric_interpretation=numeric, result=result, output=str(output),
                  seconds=time.monotonic() - started)
    print(f"{label}: " + (f"{result['classification']}, {result['wrong_words']}/112 wrong words" if numeric
                            else f"incomplete/unsupported (exit{process.returncode}); inspect logs"), flush=True)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="independent NVIDIA, AMD and WARP runs, once each")
    group.add_argument("--vendor", choices=("nvidia", "amd"))
    group.add_argument("--warp", action="store_true")
    group.add_argument("--build-only", action="store_true", help="build and run CPU checks; no graphics/device access")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This is a Windows D3D12 reproducer.")
    build()
    if args.build_only:
        return 0
    session = ROOT / "results" / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8])
    session.mkdir(parents=True)
    selections = [("nvidia", ["--vendor", "nvidia"]), ("amd", ["--vendor", "amd"]), ("warp", ["--warp"])]
    if not args.all:
        selections = [x for x in selections if x[0] == (args.vendor or "warp")]
    records = []
    print(f"Results directory: {session}", flush=True)
    for label, selector in selections:
        record = run_once(label, selector, session)
        records.append(record)
        (session / "summary.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
        if record["supervision_error"]:
            break
    print(f"Keep the entire results folder: {session}")
    if any(not x["numeric_interpretation"] for x in records):
        return 1
    return 2 if any(x["result"]["wrong_words"] for x in records) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
