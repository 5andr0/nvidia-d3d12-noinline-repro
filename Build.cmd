@echo off
rem Source-only reproducer. Use an x64 Visual Studio Developer Command Prompt.
setlocal
cd /d "%~dp0"
set "SDK_X64=%ProgramFiles(x86)%\Windows Kits\10\bin\10.0.26100.0\x64"
if not exist "%SDK_X64%\dxc.exe" (
  echo Required Windows SDK 10.0.26100.0 x64 DXC was not found.
  exit /b 1
)
if not exist "%SDK_X64%\dxil.dll" exit /b 1
set "DXC_DXIL_DLL_PATH=%SDK_X64%\dxil.dll"
if not exist build mkdir build
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /MT /O2 /W4 /WX /Febuild\generate-inputs.exe /Fobuild\generate-inputs.obj source\generate-inputs.cpp /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
build\generate-inputs.exe
if errorlevel 1 exit /b 1
"%SDK_X64%\dxc.exe" -E main -T vs_6_8 -HV 2018 -no-warnings -Ges -denorm ftz -Fo data\baseline.dxil source\baseline.hlsl
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /MT /O2 /W4 /WX /D_WIN32_WINNT=0x0A00 /Fediagnostic.exe /Fobuild\diagnostic.obj source\diagnostic.cpp /link d3d12.lib dxgi.lib bcrypt.lib /INCREMENTAL:NO
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /MT /O2 /W4 /WX /Febuild\cpu-tests.exe /Fobuild\cpu-tests.obj source\cpu-tests.cpp /link /INCREMENTAL:NO
if errorlevel 1 exit /b 1
build\cpu-tests.exe data
if errorlevel 1 exit /b 1
echo Built from source; CPU checks passed. No graphics test was executed.
echo Use Run-Tests.cmd for separate NVIDIA, AMD and WARP runs.
exit /b 0
