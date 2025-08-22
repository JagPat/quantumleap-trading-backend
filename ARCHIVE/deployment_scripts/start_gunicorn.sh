#!/bin/bash
# Emergency Railway Start Script with Gunicorn
set -e

echo "🚨 Emergency Railway Start - Using Gunicorn"
echo "📍 PORT: ${PORT:-8000}"

# Set default port if not provided
export PORT=${PORT:-8000}

# Validate PORT is numeric
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "⚠️  Invalid PORT '$PORT', using 8000"
    export PORT=8000
fi

echo "✅ Starting with PORT: $PORT"

# Use gunicorn instead of uvicorn
exec gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
