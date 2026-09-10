@echo off
rem Put ALL large caches on the repo drive (e.g. E:) under bloom\.cache\
rem Parent of this file = training\  ->  repo root = ..\
pushd "%~dp0.."
set "BLOOM_CACHE=%CD%\.cache"
popd
set "HF_HOME=%BLOOM_CACHE%\huggingface"
set "TORCH_HOME=%BLOOM_CACHE%\torch"
set "PIP_CACHE_DIR=%BLOOM_CACHE%\pip"
if not exist "%HF_HOME%" mkdir "%HF_HOME%"
if not exist "%TORCH_HOME%" mkdir "%TORCH_HOME%"
if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"
echo BLOOM_CACHE=%BLOOM_CACHE%
echo HF_HOME=%HF_HOME%
