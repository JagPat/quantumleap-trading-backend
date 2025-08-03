#!/bin/bash
# Railway Start Script - Permanent Solution
set -e

echo "🚀 Starting Quantum Leap Trading Backend on Railway..."
echo "📍 Raw PORT value: '${PORT}'"
echo "🕐 Time: $(date)"

# Validate and set PORT with proper integer handling
if [ -z "$PORT" ]; then
    VALIDATED_PORT=8000
    echo "⚠️  PORT not set, using default: $VALIDATED_PORT"
elif ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    VALIDATED_PORT=8000
    echo "⚠️  PORT '$PORT' is not a valid integer, using default: $VALIDATED_PORT"
else
    VALIDATED_PORT=$PORT
    echo "✅ PORT validated: $VALIDATED_PORT"
fi

echo "🚀 Starting uvicorn with port: $VALIDATED_PORT"

# Start the application with validated port
exec uvicorn main:app --host 0.0.0.0 --port $VALIDATED_PORT --workers 1
