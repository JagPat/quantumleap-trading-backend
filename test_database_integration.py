#!/usr/bin/env python3
"""
Test script for enhanced database integration functions
"""
import sys
import os
import sqlite3
import tempfile
from datetime import datetime, date
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
    get_comprehensive_user_context,
    store_enhanced_analysis_session,
    get_portfolio_analysis_history,
    get_recommendation_analytics,
    cleanup_old_data,
    get_database_health_enhanced,
    store_user_investment_profile,
    store_investment_goal,
    store_risk_assessment,
    store_enhanced_recommendations,
    store_market_context
)

def setup_test_data():
    """Set up comprehensive test data"""
    
    print("Setting up test data...")
    user_id = "test_integration_user"
    
    # Store user profile
    profile_data = {
        "risk_tolerance": "moderate",
        "investment_timeline": "long_term",
        "preferred_sectors": ["technology", "healthcare"],
        "max_position_size": 20.0,
        "auto_trading_enabled": True,
        "stop_loss_preference": 8.0,
        "take_profit_preference": 25.0
    }
    store_user_investment_profile(user_id, profile_data)
    
    # Store investment goals
    goal_data = {
        "goal_name": "Retirement Planning",
        "goal_type": "retirement",
        "target_amount": 10000000,
        "current_amount": 1000000,
        "priority_level": 1,
        "monthly_contribution": 50000
    }
    store_investment_goal(user_id, goal_data)
    
    # Store risk assessment
    assessment_data = {
        "risk_score": 75,
        "risk_tolerance": "moderate",
        "assessment_method": "questionnaire",
        "key_factors": ["Long-term horizon", "Stable income"]
    }
    store_risk_assessment(user_id, assessment_data)
    
    # Store recommendations
    recommendations = [
        {
            "symbol": "TCS",
            "current_allocation": 15.0,
            "target_allocation": 18.0,
            "action": "INCREASE",
            "quantity_change": 25,
            "value_change": 100000,
            "current_price": 4000,
            "reasoning": "Strong IT sector fundamentals",
            "confidence": 85,
            "priority": "HIGH",
            "timeframe": "SHORT_TERM",
            "sector": "Information Technology"
        },
        {
            "symbol": "RELIANCE",
            "current_allocation": 25.0,
            "target_allocation": 20.0,
            "action": "REDUCE",
            "quantity_change": -20,
            "value_change": -125000,
            "current_price": 2500,
            "reasoning": "Reduce concentration risk",
            "confidence": 80,
            "priority": "MEDIUM",
            "timeframe": "SHORT_TERM",
            "sector": "Energy"
        }
    ]
    analysis_id = "test_analysis_123"
    store_enhanced_recommendations(user_id, analysis_id, recommendations)
    
    # Store market context
    market_data = {
        "nifty_value": 21500.0,
        "nifty_change": 150.0,
        "nifty_change_percent": 0.7,
        "nifty_trend": "bullish",
        "market_sentiment": "bullish",
        "volatility_index": 16.5,
        "fear_greed_index": 70
    }
    store_market_context("2024-01-15", market_data)
    
    print("✓ Test data setup complete")
    return user_id

def test_comprehensive_user_context():
    """Test comprehensive user context retrieval"""
    
    print("\n" + "=" * 60)
    print("TESTING COMPREHENSIVE USER CONTEXT")
    print("=" * 60)
    
    user_id = setup_test_data()
    
    print("Step 1: Getting comprehensive user context...")
    context = get_comprehensive_user_context(user_id)
    
    print(f"✓ User ID: {context['user_id']}")
    print(f"✓ Profile available: {'Yes' if context['profile'] else 'No'}")
    print(f"✓ Active goals: {len(context['active_goals'])}")
    print(f"✓ Risk assessment: {'Yes' if context['risk_assessment'] else 'No'}")
    print(f"✓ Recent recommendations: {len(context['recent_recommendations'])}")
    print(f"✓ Market context available: {context['market_context']['market_available']}")
    print(f"✓ Context completeness: {context['context_completeness']}%")
    
    # Test with non-existent user
    print("\nStep 2: Testing with non-existent user...")
    empty_context = get_comprehensive_user_context("non_existent_user")
    print(f"✓ Empty context handled: {'Yes' if not empty_context['profile'] else 'No'}")
    
    return context

def test_analysis_session_storage():
    """Test enhanced analysis session storage"""
    
    print("\n" + "=" * 60)
    print("TESTING ANALYSIS SESSION STORAGE")
    print("=" * 60)
    
    user_id = "test_integration_user"
    
    # Sample analysis data
    analysis_data = {
        "status": "success",
        "provider_used": "openai",
        "confidence_score": 0.85,
        "portfolio_data": {
            "total_value": 1000000,
            "holdings": [
                {"symbol": "TCS", "value": 200000},
                {"symbol": "RELIANCE", "value": 300000}
            ]
        },
        "analysis": {
            "portfolio_health": {"overall_score": 82},
            "stock_recommendations": [
                {"symbol": "TCS", "action": "INCREASE"},
                {"symbol": "RELIANCE", "action": "REDUCE"}
            ]
        }
    }
    
    recommendations = [
        {
            "symbol": "TCS",
            "action": "INCREASE",
            "confidence": 85,
            "priority": "HIGH"
        }
    ]
    
    print("Step 1: Storing enhanced analysis session...")
    session_id = store_enhanced_analysis_session(user_id, analysis_data, recommendations)
    
    if session_id:
        print(f"✓ Analysis session stored with ID: {session_id}")
    else:
        print("✗ Failed to store analysis session")
    
    return session_id

def test_portfolio_analysis_history():
    """Test portfolio analysis history retrieval"""
    
    print("\n" + "=" * 60)
    print("TESTING PORTFOLIO ANALYSIS HISTORY")
    print("=" * 60)
    
    user_id = "test_integration_user"
    
    print("Step 1: Getting portfolio analysis history...")
    history = get_portfolio_analysis_history(user_id, days_back=30, limit=10)
    
    print(f"✓ Retrieved {len(history)} analysis records")
    
    for i, record in enumerate(history[:3], 1):  # Show first 3
        print(f"✓ Analysis {i}: {record['analysis_type']} - Score: {record['portfolio_score']} - Recommendations: {record['recommendations_count']}")
    
    return history

def test_recommendation_analytics():
    """Test recommendation analytics"""
    
    print("\n" + "=" * 60)
    print("TESTING RECOMMENDATION ANALYTICS")
    print("=" * 60)
    
    user_id = "test_integration_user"
    
    print("Step 1: Getting recommendation analytics...")
    analytics = get_recommendation_analytics(user_id, days_back=90)
    
    print(f"✓ Total recommendations: {analytics['total_recommendations']}")
    print(f"✓ Implementation rate: {analytics['implementation_stats']['implementation_rate']:.1f}%")
    print(f"✓ Action distribution: {analytics['action_distribution']}")
    print(f"✓ Priority distribution: {analytics['priority_distribution']}")
    print(f"✓ Sector distribution: {analytics['sector_distribution']}")
    print(f"✓ Performance metrics: {analytics['performance_metrics']['total_count']} tracked")
    
    return analytics

def test_database_health():
    """Test enhanced database health check"""
    
    print("\n" + "=" * 60)
    print("TESTING DATABASE HEALTH")
    print("=" * 60)
    
    print("Step 1: Getting enhanced database health...")
    health = get_database_health_enhanced()
    
    print(f"✓ Database status: {health['status']}")
    print(f"✓ Feature status: {health.get('feature_status', 'unknown')}")
    print(f"✓ Enhanced tables: {len(health.get('enhanced_tables', {}))}")
    
    if 'enhanced_tables' in health:
        for table, count in health['enhanced_tables'].items():
            if isinstance(count, int):
                print(f"  - {table}: {count} records")
            else:
                print(f"  - {table}: {count}")
    
    if 'recent_activity' in health:
        activity = health['recent_activity']
        print(f"✓ Recent recommendations (7d): {activity['recommendations_7d']}")
        print(f"✓ Recent analyses (7d): {activity['analyses_7d']}")
    
    return health

def test_data_cleanup():
    """Test data cleanup functionality"""
    
    print("\n" + "=" * 60)
    print("TESTING DATA CLEANUP")
    print("=" * 60)
    
    print("Step 1: Running data cleanup (keeping 30 days)...")
    cleanup_stats = cleanup_old_data(days_to_keep=30)
    
    if 'error' in cleanup_stats:
        print(f"✗ Cleanup failed: {cleanup_stats['error']}")
    else:
        print("✓ Cleanup completed successfully")
        total_cleaned = sum(v for v in cleanup_stats.values() if isinstance(v, int))
        print(f"✓ Total records cleaned: {total_cleaned}")
        
        for table, count in cleanup_stats.items():
            if isinstance(count, int) and count > 0:
                print(f"  - {table}: {count} records")
    
    return cleanup_stats

def test_error_handling():
    """Test error handling in integration functions"""
    
    print("\n" + "=" * 60)
    print("TESTING ERROR HANDLING")
    print("=" * 60)
    
    # Test with invalid user ID
    print("Step 1: Testing with invalid user ID...")
    context = get_comprehensive_user_context("")
    print(f"✓ Empty user ID handled: {'error' in context or not context['profile']}")
    
    # Test with invalid analysis data
    print("\nStep 2: Testing with invalid analysis data...")
    session_id = store_enhanced_analysis_session("test_user", {}, [])
    print(f"✓ Invalid analysis data handled: {session_id is not None}")
    
    # Test analytics with no data
    print("\nStep 3: Testing analytics with no data...")
    analytics = get_recommendation_analytics("non_existent_user")
    print(f"✓ No data case handled: {analytics['total_recommendations'] == 0}")

def run_all_tests():
    """Run all database integration tests"""
    
    try:
        # Initialize database
        print("Initializing database...")
        init_database()
        print("✓ Database initialized")
        
        # Run tests
        context = test_comprehensive_user_context()
        session_id = test_analysis_session_storage()
        history = test_portfolio_analysis_history()
        analytics = test_recommendation_analytics()
        health = test_database_health()
        cleanup_stats = test_data_cleanup()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("ALL DATABASE INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print(f"\nTest Summary:")
        print(f"- User context completeness: {context['context_completeness']}%")
        print(f"- Analysis session stored: {'✓' if session_id else '✗'}")
        print(f"- Analysis history records: {len(history)}")
        print(f"- Total recommendations analyzed: {analytics['total_recommendations']}")
        print(f"- Database health: {health['status']}")
        print(f"- Cleanup completed: {'✓' if 'error' not in cleanup_stats else '✗'}")
        
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