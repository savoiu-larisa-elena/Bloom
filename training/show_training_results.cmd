@echo off
setlocal
cd /d "%~dp0"
if exist "..\backend\venv\Scripts\python.exe" (
  set PY=..\backend\venv\Scripts\python.exe
) else (
  set PY=python
)
%PY% show_training_results.py %*
if "%~1"=="" (
  echo.
  echo Markdown report:  show_training_results.cmd --markdown
)
endlocal
