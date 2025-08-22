#!/bin/bash

# Quantum Leap Trading Platform - Railway Deployment Script

echo "🚀 Deploying Quantum Leap Trading Platform to Railway..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the project root."
    exit 1
fi

# Install Railway CLI if not present
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Login to Railway (if not already logged in)
echo "🔐 Checking Railway authentication..."
railway login

# Create or connect to Railway project
echo "🔗 Connecting to Railway project..."
railway link

# Set environment variables
echo "⚙️ Setting environment variables..."
railway variables set PORT=8000
railway variables set PYTHONPATH=/app
railway variables set PYTHONUNBUFFERED=1

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo "🌐 Your application should be available at your Railway domain"
echo "📊 Check the Railway dashboard for deployment status and logs"
