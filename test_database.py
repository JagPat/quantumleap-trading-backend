#!/usr/bin/env python3
"""
Test script to verify database functionality and generate encryption key
"""
import os
import sys
from cryptography.fernet import Fernet
from app.core.config import settings
from app.database.service import init_database, check_database_health, store_portfolio_snapshot, get_latest_portfolio_snapshot

def generate_encryption_key():
    """Generate a new encryption key"""
    key = Fernet.generate_key()
    print(f"Generated encryption key: {key.decode()}")
    print("Add this to your Railway environment variables as ENCRYPTION_KEY")
    return key.decode()

def test_database():
    """Test database functionality"""
    print("Testing database functionality...")
    print(f"Database path: {settings.database_path}")
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    # Check health
    print("Checking database health...")
    health = check_database_health()
    print(f"Health status: {health}")
    
    # Test portfolio operations
    test_user_id = "test_user_123"
    test_timestamp = "2024-01-15T10:30:00"
    test_holdings = '[{"symbol": "RELIANCE", "quantity": 100, "value": 250000}]'
    test_positions = '[{"symbol": "NIFTY", "quantity": 1, "value": 50000}]'
    
    print(f"Testing portfolio snapshot storage for user: {test_user_id}")
    success = store_portfolio_snapshot(test_user_id, test_timestamp, test_holdings, test_positions)
    print(f"Storage success: {success}")
    
    if success:
        print("Testing portfolio snapshot retrieval...")
        snapshot = get_latest_portfolio_snapshot(test_user_id)
        print(f"Retrieved snapshot: {snapshot}")
    
    print("Database test completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate-key":
        generate_encryption_key()
    else:
        test_database() 