#!/bin/bash
# Setup script for QuantumLeap Trading Backend local development

echo "🚀 Setting up QuantumLeap Trading Backend for local development..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate

# Install core dependencies first
pip install --upgrade pip

# Install pydantic with compatible version for Python 3.13
pip install "pydantic>=2.6.0"

# Install PyKiteConnect from GitHub
pip install git+https://github.com/zerodhatech/pykiteconnect.git

# Install remaining dependencies
pip install fastapi uvicorn python-multipart python-dotenv passlib bcrypt

echo "✅ All dependencies installed successfully!"

# Test imports
echo "🧪 Testing imports..."
python3 -c "from kiteconnect import KiteConnect; print('✅ kiteconnect import successful!')"
python3 -c "import main; print('✅ main.py imports successfully!')"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your configuration before running the application"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete! Your local development environment is ready."
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "🔗 Local API will be available at: http://localhost:8000"
echo "🔗 API documentation: http://localhost:8000/docs"
echo ""
echo "🚀 Production API is running at: https://web-production-de0bc.up.railway.app" 