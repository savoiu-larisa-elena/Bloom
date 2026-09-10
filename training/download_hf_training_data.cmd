@echo off
setlocal
cd /d "%~dp0"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
call "%~dp0set_bloom_cache_env.cmd"
echo.
if not exist "..\backend\venv\Scripts\python.exe" (
  echo ERROR: Missing ..\backend\venv\Scripts\python.exe
  echo Create the backend venv first: cd ..\backend ^& python -m venv venv
  pause
  exit /b 1
)
"..\backend\venv\Scripts\python.exe" -m pip install -q datasets
echo.
echo [1/3] JFLEG -^> data\jfleg_from_hf.jsonl
"..\backend\venv\Scripts\python.exe" prepare_hf_dataset.py --dataset jfleg --output data\jfleg_from_hf.jsonl
if errorlevel 1 goto fail
echo.
echo [2/3] dair-ai/emotion -^> data\emotion_train.jsonl
"..\backend\venv\Scripts\python.exe" prepare_hf_dataset.py --dataset emotion --output data\emotion_train.jsonl
if errorlevel 1 goto fail
echo.
echo [3/3] PAWS paraphrases -^> data\paraphrase_train.jsonl  (cap 25000 pairs; edit .cmd to change)
"..\backend\venv\Scripts\python.exe" prepare_hf_dataset.py --dataset paws --output data\paraphrase_train.jsonl --max-rows 25000
if errorlevel 1 goto fail
echo.
echo OK. Next: install_train_deps.cmd then train_*.cmd / train_all.cmd
pause
exit /b 0
:fail
echo FAILED.
pause
exit /b 1
