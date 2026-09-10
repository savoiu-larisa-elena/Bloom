@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_bloom_cache_env.cmd"
if not exist "..\backend\venv\Scripts\python.exe" (
  echo ERROR: Missing ..\backend\venv\Scripts\python.exe
  pause
  exit /b 1
)
if not exist "data\jfleg_from_hf.jsonl" (
  echo ERROR: data\jfleg_from_hf.jsonl not found. Run download_jfleg.cmd first.
  pause
  exit /b 1
)
echo Training with data\jfleg_from_hf.jsonl - this may take a long time on CPU.
"..\backend\venv\Scripts\python.exe" train_gec.py --data data\jfleg_from_hf.jsonl --output outputs\gec-finetuned
if errorlevel 1 (
  echo FAILED. On CPU try: train_gec_cpu_small.cmd  or add --no-fp16 --batch-size 2
  pause
  exit /b 1
)
echo Done. Set BLOOM_NEURAL_GRAMMAR_MODEL to outputs\gec-finetuned - see QUICKSTART.md
exit
