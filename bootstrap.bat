@echo off

:: Check if Python is installed
python --version 2>nul
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.6+.
    exit /b 1
)

:: Create virtual environment
python -m venv venv
echo Virtual environment created.

:: Activate the virtual environment
call venv\Scripts\activate
echo Virtual environment activated.

:: Install the requirements
if exist requirements.txt (
    pip install --upgrade pip
    pip install -r requirements.txt
    echo Requirements installed.
) else (
    echo requirements.txt not found.
)

echo Setup complete. You can now run your project.
pause
