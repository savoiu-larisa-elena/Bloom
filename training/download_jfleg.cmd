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
echo Installing datasets package...
"..\backend\venv\Scripts\python.exe" -m pip install -q datasets
echo.
echo Downloading JFLEG from Hugging Face and writing data\jfleg_from_hf.jsonl ...
"..\backend\venv\Scripts\python.exe" prepare_hf_dataset.py --dataset jfleg --output data\jfleg_from_hf.jsonl
if errorlevel 1 (
  echo FAILED.
  echo If you saw "not enough space on the disk": free space on C: or keep HF_HOME on this drive ^(see QUICKSTART.md^).
  pause
  exit /b 1
)
echo.
echo OK. Next: install_train_deps.cmd then train_gec_jfleg.cmd
pause
