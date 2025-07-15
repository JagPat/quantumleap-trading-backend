import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "trading_app.db")

# Encryption configuration
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Railway deployment configuration
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "development")
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Kite Connect configuration
KITE_API_TIMEOUT = int(os.getenv("KITE_API_TIMEOUT", 30))
KITE_API_RETRIES = int(os.getenv("KITE_API_RETRIES", 3)) 