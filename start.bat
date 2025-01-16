@echo off
:: Set encoding to CP866
chcp 866 > nul
setlocal enabledelayedexpansion

echo Starting One Window...
echo ==================
echo.

:: Check Python installation
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed! Please install Python 3.x
    echo Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo OK: Found Python version %PYTHON_VERSION%
echo.

:: Check virtual environment
if not exist "venv" (
    echo INFO: Creating new virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        echo.
        pause
        exit /b 1
    )
    echo OK: Virtual environment created
) else (
    echo OK: Found existing virtual environment
)
echo.

:: Activate virtual environment
echo INFO: Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo.
    pause
    exit /b 1
)
echo OK: Virtual environment activated
echo.

:: Check dependencies
pip freeze | findstr "Flask" > nul
if errorlevel 1 (
    echo INFO: Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        echo.
        pause
        exit /b 1
    )
    echo OK: Dependencies installed
) else (
    echo OK: Dependencies already installed
)
echo.

:: Start application
echo INFO: Starting One Window...
echo Press Ctrl+C to stop
echo.

python app.py
if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start!
    echo.
    pause
    exit /b 1
)

:: Wait for input before exit
echo.
echo Press any key to exit...
pause > nul
