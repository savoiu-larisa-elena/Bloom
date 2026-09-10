@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_bloom_cache_env.cmd"
if not exist "..\backend\venv\Scripts\python.exe" (
  echo ERROR: Missing ..\backend\venv\Scripts\python.exe
  pause
  exit /b 1
)
if not exist "data\my_pairs.jsonl" (
  echo ERROR: data\my_pairs.jsonl not found. Add some lines or use download_jfleg.cmd + train_gec_jfleg.cmd
  pause
  exit /b 1
)
echo Small CPU run: my_pairs.jsonl, --no-fp16, batch-size 2
"..\backend\venv\Scripts\python.exe" train_gec.py --data data\my_pairs.jsonl --output outputs\gec-finetuned --no-fp16 --batch-size 2 --epochs 1
if errorlevel 1 (
  echo FAILED.
  pause
  exit /b 1
)
echo Done. Set BLOOM_NEURAL_GRAMMAR_MODEL to outputs\gec-finetuned - see QUICKSTART.md
pause
