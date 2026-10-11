@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
 echo Cadenza needs Python 3.11+ with Tk. Install Python with PATH enabled, then reopen this launcher.
 start https://www.python.org/downloads/
 pause
 exit /b 1
)
python desktop.py
if errorlevel 1 pause
