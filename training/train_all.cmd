@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_bloom_cache_env.cmd"
if not exist "..\backend\venv\Scripts\python.exe" (
  echo ERROR: ..\backend\venv\Scripts\python.exe not found.
  pause
  exit /b 1
)
set PY=..\backend\venv\Scripts\python.exe

echo === [1/3] Grammar correction (GEC) ===
if not exist "data\jfleg_from_hf.jsonl" (
  echo Run download_jfleg.cmd first to create data\jfleg_from_hf.jsonl
  pause
  exit /b 1
)
%PY% train_gec.py --data data\jfleg_from_hf.jsonl --output outputs\gec-finetuned
if errorlevel 1 goto :fail

echo.
echo === [2/3] Emotion (needs data\emotion_train.jsonl) ===
if not exist "data\emotion_train.jsonl" (
  echo Missing data\emotion_train.jsonl - skipping emotion training.
  goto :paraphrase
)
%PY% train_emotion.py --data data\emotion_train.jsonl --output outputs\emotion-finetuned
if errorlevel 1 goto :fail

:paraphrase
echo.
echo === [3/3] Paraphrase (needs data\paraphrase_train.jsonl) ===
if not exist "data\paraphrase_train.jsonl" (
  echo Missing data\paraphrase_train.jsonl - skipping paraphrase training.
  goto :env
)
%PY% train_paraphrase.py --data data\paraphrase_train.jsonl --output outputs\paraphrase-finetuned
if errorlevel 1 goto :fail

:env
echo.
echo === Point Bloom at your checkpoints (PowerShell) ===
echo   $env:BLOOM_NEURAL_GRAMMAR_MODEL="%~dp0outputs\gec-finetuned"
echo   $env:BLOOM_EMOTION_MODEL="%~dp0outputs\emotion-finetuned"
echo   $env:BLOOM_PARAPHRASE_MODEL="%~dp0outputs\paraphrase-finetuned"
echo.
pause
exit /b 0

:fail
echo FAILED.
pause
exit /b 1
