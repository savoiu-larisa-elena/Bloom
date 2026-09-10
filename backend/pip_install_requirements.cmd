@echo off
REM Run from Explorer double-click, or: cmd /c pip_install_requirements.cmd
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
exit /b %ERRORLEVEL%
