@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_bloom_cache_env.cmd"
if not exist "..\backend\venv\Scripts\python.exe" (
  echo ERROR: backend venv not found.
  pause
  exit /b 1
)
set PY=..\backend\venv\Scripts\python.exe
echo Downloads can take a while. GEC bulk is ~3k lines; emotion/paraphrase are much larger.
echo.
echo [1/3] GEC (JFLEG, all correction refs^)
%PY% prepare_bulk_datasets.py gec --output data\gec_bulk.jsonl
if errorlevel 1 goto :fail
echo.
echo [2/3] Emotion (dair-ai + go_emotions^)
%PY% prepare_bulk_datasets.py emotion --output data\emotion_bulk.jsonl
if errorlevel 1 goto :fail
echo.
echo [3/3] Paraphrase (PAWS^)
%PY% prepare_bulk_datasets.py paraphrase --output data\paraphrase_bulk.jsonl
if errorlevel 1 goto :fail
echo.
echo JSONL written under data\. For more GEC lines, append my_pairs.jsonl:  copy /b data\gec_bulk.jsonl+data\my_pairs.jsonl data\gec_merged.jsonl
echo Next: train_bulk.cmd
pause
exit /b 0
:fail
echo FAILED.
pause
exit /b 1
