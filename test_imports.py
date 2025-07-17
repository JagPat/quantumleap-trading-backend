#!/usr/bin/env python3
"""
Test script to verify FastAPI and Pydantic imports work correctly
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    print("Testing imports...")
    
    try:
        import fastapi
        print(f"FastAPI imported successfully: {fastapi.__version__}")
    except ImportError as e:
        print(f"FastAPI import failed: {e}")
        return False
    
    try:
        from fastapi.middleware.cors import CORSMiddleware
        print("FastAPI CORS middleware imported successfully")
    except ImportError as e:
        print(f"FastAPI CORS middleware import failed: {e}")
        return False
    
    try:
        import pydantic
        print(f"Pydantic imported successfully: {pydantic.__version__}")
    except ImportError as e:
        print(f"Pydantic import failed: {e}")
        return False
    
    try:
        from pydantic import BaseModel
        print("Pydantic BaseModel imported successfully")
    except ImportError as e:
        print(f"Pydantic BaseModel import failed: {e}")
        return False
    
    try:
        import uvicorn
        print(f"Uvicorn imported successfully: {uvicorn.__version__}")
    except ImportError as e:
        print(f"Uvicorn import failed: {e}")
        return False
    
    try:
        from app.core.config import settings
        print("App config imported successfully")
    except ImportError as e:
        print(f"App config import failed: {e}")
        return False
    
    print("All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 