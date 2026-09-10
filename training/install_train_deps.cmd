@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_bloom_cache_env.cmd"
if not exist "..\backend\venv\Scripts\python.exe" (
  echo ERROR: Missing ..\backend\venv\Scripts\python.exe
  pause
  exit /b 1
)
"..\backend\venv\Scripts\python.exe" -m pip install -r requirements-train.txt
if errorlevel 1 (
  echo FAILED.
  pause
  exit /b 1
)
echo OK.
exit
