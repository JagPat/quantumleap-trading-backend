#!/usr/bin/env python3
"""
Database cleanup script to remove malformed portfolio data
"""
import sqlite3
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = "trading_app.db"
USER_ID_TO_CLEAN = "EBW183"

def clean_portfolio_data():
    """Clean malformed portfolio data for the specified user"""
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        logger.info(f"Connected to database: {DATABASE_PATH}")
        
        # First, let's see what portfolio data exists for this user
        cursor.execute("""
            SELECT id, user_id, timestamp, created_at 
            FROM portfolio_snapshots 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (USER_ID_TO_CLEAN,))
        
        existing_snapshots = cursor.fetchall()
        logger.info(f"Found {len(existing_snapshots)} portfolio snapshots for user {USER_ID_TO_CLEAN}")
        
        if not existing_snapshots:
            logger.info(f"No portfolio data found for user {USER_ID_TO_CLEAN}")
            return
        
        # Show existing snapshots
        for snapshot in existing_snapshots:
            logger.info(f"Snapshot ID: {snapshot[0]}, User: {snapshot[1]}, Timestamp: {snapshot[2]}, Created: {snapshot[3]}")
        
        # Delete all portfolio snapshots for this user
        cursor.execute("""
            DELETE FROM portfolio_snapshots 
            WHERE user_id = ?
        """, (USER_ID_TO_CLEAN,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Successfully deleted {deleted_count} portfolio snapshots for user {USER_ID_TO_CLEAN}")
        
        # Verify deletion
        cursor.execute("""
            SELECT COUNT(*) 
            FROM portfolio_snapshots 
            WHERE user_id = ?
        """, (USER_ID_TO_CLEAN,))
        
        remaining_count = cursor.fetchone()[0]
        logger.info(f"Remaining portfolio snapshots for user {USER_ID_TO_CLEAN}: {remaining_count}")
        
        conn.close()
        logger.info("Database cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database cleanup: {str(e)}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Portfolio Data Cleanup Script ===")
    print(f"Target user: {USER_ID_TO_CLEAN}")
    print(f"Database: {DATABASE_PATH}")
    print()
    
    response = input("Do you want to proceed with cleaning portfolio data? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        clean_portfolio_data()
    else:
        print("Cleanup cancelled.") 