@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if not exist "diagnostic.exe" exit /b 1
set "stamp=%DATE%_%TIME%_%RANDOM%"
set "stamp=%stamp:/=-%"
set "stamp=%stamp::=-%"
set "stamp=%stamp: =_%"
set "stamp=%stamp:.=-%"
set "session=%~dp0results-%stamp%"
if exist "%session%" exit /b 1
mkdir "%session%"
if errorlevel 1 exit /b 1
>"%session%\summary.txt" echo Fixed baseline: three explicit independent selections, one draw each, no retry.
call :run nvidia --vendor nvidia
call :run amd --vendor amd
call :run warp --warp
echo Results summary: "%session%\summary.txt"
type "%session%\summary.txt"
exit /b 0

:run
"%~dp0diagnostic.exe" %2 %3 --output "%session%\%1" 1>"%session%\%1.stdout.txt" 2>"%session%\%1.stderr.txt"
set "runexit=%ERRORLEVEL%"
>>"%session%\summary.txt" echo [%1] process exit=%runexit%
if not "%runexit%"=="0" >>"%session%\summary.txt" echo Numeric interpretation invalid unless exit=0. Exit2 is UNSUPPORTED; other nonzero is INCOMPLETE/ERROR.
if exist "%session%\%1\result.json" type "%session%\%1\result.json" >>"%session%\summary.txt"
if not exist "%session%\%1\result.json" >>"%session%\summary.txt" echo INCOMPLETE/ERROR: no final result.json; inspect separate logs and retained raw files.
exit /b 0
