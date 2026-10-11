@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Install Python 3.11 or later with Tk support & pause & exit /b 1)
python desktop.py
if errorlevel 1 pause
