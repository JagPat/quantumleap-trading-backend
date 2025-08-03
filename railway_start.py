#!/usr/bin/env python3
"""
Railway Start Script

This script ensures proper port handling for Railway deployment.
"""

import os
import sys
import subprocess

def main():
    """Start the application with proper port handling"""
    
    # Get port from environment with robust handling
    port_env = os.environ.get("PORT", "8000")
    
    # Handle empty or invalid PORT values
    if not port_env or port_env.strip() == "":
        port = "8000"
        print(f"⚠️  PORT environment variable is empty, using default: {port}")
        os.environ["PORT"] = port
    else:
        port = port_env.strip()
        try:
            # Validate that it's a valid integer
            int(port)
            print(f"✅ Using PORT from environment: {port}")
        except ValueError:
            port = "8000"
            print(f"⚠️  Invalid PORT value '{port_env}', using default: {port}")
            os.environ["PORT"] = port
    
    # Set other required environment variables
    os.environ["PYTHONPATH"] = "/app"
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    print(f"🚀 Starting Quantum Leap Trading Platform")
    print(f"   Host: 0.0.0.0")
    print(f"   Port: {port}")
    print(f"   Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    
    # Start uvicorn with proper arguments
    cmd = [
        "python", "-m", "uvicorn", 
        "main:app",
        "--host", "0.0.0.0",
        "--port", port,
        "--log-level", "info"
    ]
    
    print(f"   Command: {' '.join(cmd)}")
    
    # Execute the command
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Application stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()