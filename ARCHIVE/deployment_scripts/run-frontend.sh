#!/bin/bash

# QuantumLeap Frontend Runner
# This script sets up and runs the frontend development server

echo "🚀 Starting QuantumLeap Frontend..."
echo "=================================="

# Check if we're in the right directory
if [ ! -d "quantum-leap-frontend" ]; then
    echo "❌ Error: quantum-leap-frontend directory not found"
    echo "Please run this script from the root directory of the project"
    exit 1
fi

# Navigate to frontend directory
cd quantum-leap-frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed successfully"
else
    echo "✅ Dependencies already installed"
fi

# Check if .env file exists, create if not
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file..."
    cat > .env << EOF
# Frontend Environment Variables
VITE_API_URL=https://web-production-de0bc.up.railway.app/api
VITE_APP_NAME=QuantumLeap Trading
VITE_APP_VERSION=2.0.0
EOF
    echo "✅ .env file created"
fi

echo ""
echo "🌐 Frontend will be available at: http://localhost:5173"
echo "🔗 Backend API URL: https://web-production-de0bc.up.railway.app/api"
echo ""
echo "Starting development server..."
echo "=================================="

# Start the development server
npm run dev