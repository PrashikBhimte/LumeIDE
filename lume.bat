@echo off
setlocal

set "PROJECT_DIR=%~d0"
cd /d %PROJECT_DIR%

if not exist "venv\Scripts\pythonw.exe" (
    echo [Error] Virtual environment not found in %PROJECT_DIR%venv
    echo Please run 'python -m venv venv' and 'pip install -r requirements.txt' first.
    pause
    exit /b
)

echo Lanuching Lume IDE
start "" "venv\Scripts\pythonw.exe" "main.py"

exit