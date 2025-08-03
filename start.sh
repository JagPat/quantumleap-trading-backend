#!/bin/bash

# Quantum Leap Trading Platform - Start Script
# Fixed version for Railway deployment

echo "🚀 Starting Quantum Leap Trading Platform..."
echo "   Port: $PORT"
echo "   Environment: $RAILWAY_ENVIRONMENT"
echo "   Time: $(date)"

# Ensure we're in the right directory
cd /app

# Start the application with uvicorn
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
