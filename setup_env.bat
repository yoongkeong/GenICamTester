@echo off
:: Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Installing Python...
    :: Download Python installer (you can change the link to the latest version if needed)
    powershell -Command "Start-Process 'https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe' -Wait"
    echo Make sure to select "Add Python to PATH" during installation.
    pause
) else (
    echo Python is already installed.
)

:: Create and activate virtual environment
echo Setting up virtual environment...
python -m venv env
if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
) else (
    echo Failed to create virtual environment. Exiting.
    exit /b 1
)

:: Upgrade pip to ensure compatibility with the latest packages
echo Upgrading pip...
python -m pip install --upgrade pip

:: Check if requirements.txt exists
if not exist requirements.txt (
    echo "requirements.txt not found in the current directory. Make sure it is present and try again."
    exit /b 1
)

:: Install pip dependencies from requirements.txt
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo "Failed to install dependencies from requirements.txt. Exiting."
    exit /b 1
)

:: Install Node.js if not present (required for npm to install Bootstrap)
echo Checking Node.js installation...
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo Node.js not found. Installing Node.js...
    :: Download Node.js installer (you can change the link to the latest version if needed)
    powershell -Command "Start-Process 'https://nodejs.org/dist/v16.13.0/node-v16.13.0-x64.msi' -Wait"
) else (
    echo Node.js is already installed.
)

:: Install Bootstrap via npm
echo Installing Bootstrap...
npm install bootstrap

:: Open Visual Studio Code in current folder
echo Launching Visual Studio Code...
code .

echo Setup complete!
pause
