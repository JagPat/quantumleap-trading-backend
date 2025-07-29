#!/usr/bin/env python3
"""
Test script for enhanced recommendations database schema
"""
import sys
import os
import sqlite3
import tempfile
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock the settings for testing
class MockSettings:
    def __init__(self, db_path):
        self.database_path = db_path
    
    def get_encryption_key(self):
        from cryptography.fernet import Fernet
        return Fernet.generate_key()

# Replace the settings import
import app.database.service as db_service
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
temp_db.close()
db_service.settings = MockSettings(temp_db.name)

# Reinitialize cipher suite with new key
from cryptography.fernet import Fernet
db_service.cipher_suite = Fernet(db_service.settings.get_encryption_key())

from app.database.service import (
    init_database,
    store_enhanced_recommendations,
    get_enhanced_recommendations,
    update_recommendation_status,
    get_recommendation_performance,
    get_recommendations_by_ids,
    cleanup_expired_recommendations
)

def test_database_schema():
    """Test the enhanced recommendations database schema"""
    
    print("=" * 60)
    print("TESTING ENHANCED RECOMMENDATIONS DATABASE SCHEMA")
    print("=" * 60)
    
    # Initialize database
    print("Step 1: Initializing database...")
    init_database()
    
    # Check if tables were created
    conn = sqlite3.connect(db_service.settings.database_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['enhanced_recommendations', 'recommendation_performance']
    for table in required_tables:
        if table in tables:
            print(f"✓ Table '{table}' created successfully")
        else:
            print(f"✗ Table '{table}' NOT found")
    
    # Check table structure
    cursor.execute("PRAGMA table_info(enhanced_recommendations)")
    columns = cursor.fetchall()
    print(f"✓ enhanced_recommendations table has {len(columns)} columns")
    
    cursor.execute("PRAGMA table_info(recommendation_performance)")
    columns = cursor.fetchall()
    print(f"✓ recommendation_performance table has {len(columns)} columns")
    
    conn.close()

def test_recommendation_storage():
    """Test storing and retrieving recommendations"""
    
    print("\n" + "=" * 60)
    print("TESTING RECOMMENDATION STORAGE")
    print("=" * 60)
    
    user_id = "test_user_123"
    analysis_id = "analysis_456"
    
    # Sample recommendations
    sample_recommendations = [
        {
            "symbol": "RELIANCE",
            "current_allocation": 25.0,
            "target_allocation": 15.0,
            "action": "REDUCE",
            "quantity_change": -40,
            "value_change": -100000,
            "current_price": 2500,
            "reasoning": "Overweight position needs reduction for better diversification",
            "confidence": 85,
            "priority": "HIGH",
            "timeframe": "SHORT_TERM",
            "expected_impact": "Reduce concentration risk by 10%",
            "risk_warning": "Large position reduction may impact returns if stock outperforms",
            "auto_trading_eligible": True,
            "sector": "Energy"
        },
        {
            "symbol": "TCS",
            "current_allocation": 20.0,
            "target_allocation": 22.0,
            "action": "INCREASE",
            "quantity_change": 15,
            "value_change": 60000,
            "current_price": 4000,
            "reasoning": "Technology sector showing strong fundamentals",
            "confidence": 80,
            "priority": "MEDIUM",
            "timeframe": "LONG_TERM",
            "expected_impact": "Increase exposure to high-growth technology sector",
            "risk_warning": "Technology stocks can be volatile",
            "auto_trading_eligible": False,
            "sector": "Technology"
        }
    ]
    
    # Test storing recommendations
    print("Step 1: Storing recommendations...")
    success = store_enhanced_recommendations(user_id, analysis_id, sample_recommendations)
    print(f"✓ Storage result: {'SUCCESS' if success else 'FAILED'}")
    
    # Test retrieving recommendations
    print("\nStep 2: Retrieving recommendations...")
    retrieved = get_enhanced_recommendations(user_id)
    print(f"✓ Retrieved {len(retrieved)} recommendations")
    
    if retrieved:
        first_rec = retrieved[0]
        print(f"✓ First recommendation: {first_rec['symbol']} - {first_rec['action']}")
        print(f"✓ Confidence: {first_rec['confidence']}%")
        print(f"✓ Priority: {first_rec['priority']}")
        print(f"✓ Auto-trading eligible: {first_rec['auto_trading_eligible']}")
    
    # Test filtering
    print("\nStep 3: Testing filters...")
    high_priority = get_enhanced_recommendations(user_id, priority="HIGH")
    print(f"✓ High priority recommendations: {len(high_priority)}")
    
    reliance_recs = get_enhanced_recommendations(user_id, symbol="RELIANCE")
    print(f"✓ RELIANCE recommendations: {len(reliance_recs)}")
    
    return retrieved

def test_recommendation_status_updates(recommendations):
    """Test updating recommendation status"""
    
    print("\n" + "=" * 60)
    print("TESTING RECOMMENDATION STATUS UPDATES")
    print("=" * 60)
    
    if not recommendations:
        print("No recommendations to test with")
        return
    
    user_id = "test_user_123"
    rec_id = recommendations[0]['id']
    
    print(f"Step 1: Updating recommendation {rec_id} to IMPLEMENTED...")
    success = update_recommendation_status(
        rec_id, user_id, "IMPLEMENTED", "MANUAL", 2450.0
    )
    print(f"✓ Update result: {'SUCCESS' if success else 'FAILED'}")
    
    # Verify the update
    updated_recs = get_enhanced_recommendations(user_id, status="IMPLEMENTED")
    print(f"✓ Implemented recommendations: {len(updated_recs)}")
    
    if updated_recs:
        print(f"✓ Status: {updated_recs[0]['implementation_status']}")
        print(f"✓ Method: {updated_recs[0]['implementation_method']}")

def test_performance_tracking():
    """Test recommendation performance tracking"""
    
    print("\n" + "=" * 60)
    print("TESTING PERFORMANCE TRACKING")
    print("=" * 60)
    
    user_id = "test_user_123"
    
    print("Step 1: Getting performance metrics...")
    performance = get_recommendation_performance(user_id, days=30)
    
    print(f"✓ Total recommendations: {performance['total_count']}")
    print(f"✓ Implemented: {performance['implemented_count']}")
    print(f"✓ Successful: {performance['successful_count']}")
    print(f"✓ Accuracy rate: {performance['accuracy_rate']:.1f}%")
    print(f"✓ Average return: {performance['average_return']:.2f}")
    print(f"✓ Detailed results: {len(performance['detailed_results'])}")

def test_recommendation_retrieval_by_ids():
    """Test retrieving recommendations by IDs"""
    
    print("\n" + "=" * 60)
    print("TESTING RECOMMENDATION RETRIEVAL BY IDS")
    print("=" * 60)
    
    user_id = "test_user_123"
    
    # Get all recommendations first
    all_recs = get_enhanced_recommendations(user_id)
    if not all_recs:
        print("No recommendations to test with")
        return
    
    # Test retrieving by IDs
    rec_ids = [rec['id'] for rec in all_recs[:2]]  # First 2 IDs
    print(f"Step 1: Retrieving recommendations by IDs: {rec_ids}")
    
    retrieved_by_ids = get_recommendations_by_ids(rec_ids, user_id)
    print(f"✓ Retrieved {len(retrieved_by_ids)} recommendations by IDs")
    
    for rec in retrieved_by_ids:
        print(f"✓ ID {rec['id']}: {rec['symbol']} - {rec['action']}")

def test_cleanup_expired():
    """Test cleanup of expired recommendations"""
    
    print("\n" + "=" * 60)
    print("TESTING EXPIRED RECOMMENDATIONS CLEANUP")
    print("=" * 60)
    
    print("Step 1: Running cleanup...")
    expired_count = cleanup_expired_recommendations()
    print(f"✓ Cleaned up {expired_count} expired recommendations")

def run_all_tests():
    """Run all database schema tests"""
    
    try:
        test_database_schema()
        recommendations = test_recommendation_storage()
        test_recommendation_status_updates(recommendations)
        test_performance_tracking()
        test_recommendation_retrieval_by_ids()
        test_cleanup_expired()
        
        print("\n" + "=" * 60)
        print("ALL DATABASE SCHEMA TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            os.unlink(temp_db.name)
            print(f"✓ Cleaned up temporary database: {temp_db.name}")
        except:
            pass

if __name__ == "__main__":
    run_all_tests()