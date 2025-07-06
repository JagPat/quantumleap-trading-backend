@echo off
REM QuantumLeap Trading Backend Quick Start Script for Windows

echo 🚀 Starting QuantumLeap Trading Backend...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "main.py" (
    echo ❌ Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo ⚙️ Creating environment configuration...
    copy env.example .env
    
    REM Generate encryption key
    python -c "from cryptography.fernet import Fernet; import os; key = Fernet.generate_key().decode(); content = open('.env', 'r').read(); open('.env', 'w').write(content.replace('your_encryption_key_here', key))"
    
    echo ✅ Environment file created at .env
    echo 🔑 Encryption key generated automatically
)

REM Start the server
echo 🌟 Starting the backend server...
python run.py

pause 