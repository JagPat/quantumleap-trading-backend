#!/bin/bash
# Railway Start Script
set -e

echo "🚀 Starting Quantum Leap Trading Backend on Railway..."
echo "📍 Port: ${PORT:-8000}"
echo "🕐 Time: $(date)"

# Ensure port is properly set
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "⚠️  PORT not set, defaulting to 8000"
else
    echo "✅ PORT set to: $PORT"
fi

# Start the application with proper port handling
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
