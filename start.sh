#!/bin/bash

# Quantum Leap Trading Platform - Start Script
# Fixed version for Railway deployment with proper port handling

echo "🚀 Starting Quantum Leap Trading Platform..."
echo "   Raw PORT: '$PORT'"
echo "   Environment: $RAILWAY_ENVIRONMENT"
echo "   Time: $(date)"

# Set default port if PORT is empty or not set
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "   PORT was empty, setting to default: $PORT"
else
    echo "   Using PORT: $PORT"
fi

# Ensure we're in the right directory
cd /app

# Start the application with uvicorn
echo "   Starting uvicorn with host=0.0.0.0 port=$PORT"
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
