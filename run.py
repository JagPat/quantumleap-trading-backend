#!/usr/bin/env python3
"""
Startup script for QuantumLeap Trading Backend API
"""

import uvicorn
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOST, PORT, DEBUG, LOG_LEVEL, IS_RAILWAY

if __name__ == "__main__":
    print("Starting QuantumLeap Trading Backend API...")
    print(f"Server will run on: http://{HOST}:{PORT}")
    print(f"Debug mode: {DEBUG}")
    print(f"Log level: {LOG_LEVEL}")
    print(f"Railway deployment: {IS_RAILWAY}")
    
    # Ensure we're using the Railway PORT if available
    railway_port = os.environ.get("PORT")
    if railway_port:
        PORT = int(railway_port)
        print(f"Using Railway PORT: {PORT}")
    
    uvicorn.run(
        "main:app",  # Correct module reference
        host=HOST,
        port=PORT,
        reload=DEBUG and not IS_RAILWAY,  # Disable reload in production
        log_level=LOG_LEVEL.lower(),
        access_log=True
    ) 