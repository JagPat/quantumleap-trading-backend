#!/usr/bin/env python3
"""
Startup script for QuantumLeap Trading Backend API
"""

import uvicorn
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the new modular config structure
from app.core.config import settings

if __name__ == "__main__":
    print("Starting QuantumLeap Trading Backend API...")
    
    # Use Railway PORT if available, otherwise use default
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Server will run on: http://{host}:{port}")
    print(f"Debug mode: {settings.debug}")
    print(f"Log level: {settings.log_level}")
    print(f"Railway deployment: {os.environ.get('RAILWAY_ENVIRONMENT') is not None}")
    
    uvicorn.run(
        "main:app",  # Correct module reference
        host=host,
        port=port,
        reload=settings.debug and not os.environ.get('RAILWAY_ENVIRONMENT'),  # Disable reload in production
        log_level=settings.log_level.lower(),
        access_log=True
    ) 