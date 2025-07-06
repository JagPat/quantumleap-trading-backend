#!/bin/bash

# QuantumLeap Trading Backend Quick Start Script

echo "🚀 Starting QuantumLeap Trading Backend..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "❌ Please run this script from the project root directory."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source backend/venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "⚙️  Creating environment configuration..."
    cp backend/env.example backend/.env
    
    # Generate encryption key
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Update .env file with generated key
    sed -i "s/your_encryption_key_here/$ENCRYPTION_KEY/" backend/.env
    
    echo "✅ Environment file created at backend/.env"
    echo "🔑 Encryption key generated automatically"
fi

# Start the server
echo "🌟 Starting the backend server..."
cd backend
python run.py 