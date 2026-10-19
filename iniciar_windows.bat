@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" frontend.py
) else (
  python frontend.py
)
if errorlevel 1 pause
