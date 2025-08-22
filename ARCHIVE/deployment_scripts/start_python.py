#!/usr/bin/env python3
"""
Emergency Python Startup Script for Railway
Handles PORT environment variable with maximum safety
"""
import os
import sys
import subprocess

def safe_start():
    """Start the application with safe port handling"""
    print("🚨 Emergency Python Startup")
    
    # Get PORT with multiple fallbacks
    port = None
    
    # Try environment variable
    port_env = os.environ.get('PORT')
    if port_env:
        try:
            port = int(port_env)
            print(f"✅ Using PORT from environment: {port}")
        except (ValueError, TypeError):
            print(f"⚠️  Invalid PORT environment variable: {port_env}")
    
    # Fallback to default
    if port is None:
        port = 8000
        print(f"✅ Using default PORT: {port}")
    
    # Validate port range
    if not (1 <= port <= 65535):
        port = 8000
        print(f"⚠️  PORT out of range, using default: {port}")
    
    print(f"🚀 Starting application on port {port}")
    
    # Start with uvicorn
    try:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
    except ImportError:
        print("❌ uvicorn not available, trying gunicorn")
        try:
            subprocess.run([
                "gunicorn", "main:app", 
                "-w", "1", 
                "-k", "uvicorn.workers.UvicornWorker",
                "--bind", f"0.0.0.0:{port}"
            ])
        except Exception as e:
            print(f"❌ Failed to start with gunicorn: {e}")
            sys.exit(1)

if __name__ == "__main__":
    safe_start()
