@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_bloom_cache_env.cmd"
if exist "..\backend\venv\Scripts\python.exe" (
  set PY=..\backend\venv\Scripts\python.exe
) else (
  set PY=python
)
echo Installing eval dependencies if needed...
"%PY%" -m pip install -q -r requirements-eval.txt
if "%~1"=="" (
  echo Running full evaluation - paraphrase capped at 500 val rows, use --full for all
  "%PY%" evaluate_checkpoints.py --task all
) else (
  "%PY%" evaluate_checkpoints.py %*
)
echo.
echo Results: eval_results\EVALUATION_REPORT.md
endlocal
