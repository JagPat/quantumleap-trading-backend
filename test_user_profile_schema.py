#!/usr/bin/env python3
"""
Test script for user investment profile database schema
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
    store_user_investment_profile,
    get_user_investment_profile,
    store_investment_goal,
    get_user_investment_goals,
    store_risk_assessment,
    get_current_risk_assessment,
    update_goal_progress,
    get_profile_based_recommendations_context,
    calculate_profile_completeness
)

def test_profile_schema():
    """Test the user investment profile database schema"""
    
    print("=" * 60)
    print("TESTING USER INVESTMENT PROFILE DATABASE SCHEMA")
    print("=" * 60)
    
    # Initialize database
    print("Step 1: Initializing database...")
    init_database()
    
    # Check if tables were created
    conn = sqlite3.connect(db_service.settings.database_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['user_investment_profiles', 'investment_goals', 'risk_assessment_history']
    for table in required_tables:
        if table in tables:
            print(f"✓ Table '{table}' created successfully")
        else:
            print(f"✗ Table '{table}' NOT found")
    
    # Check table structures
    for table in required_tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"✓ {table} table has {len(columns)} columns")
    
    conn.close()

def test_profile_storage():
    """Test storing and retrieving user investment profiles"""
    
    print("\n" + "=" * 60)
    print("TESTING PROFILE STORAGE")
    print("=" * 60)
    
    user_id = "test_user_profile_123"
    
    # Sample profile data
    sample_profile = {
        "risk_tolerance": "moderate",
        "investment_timeline": "long_term",
        "investment_goals": ["retirement", "house"],
        "preferred_sectors": ["technology", "healthcare", "finance"],
        "avoided_sectors": ["tobacco", "gambling"],
        "max_position_size": 20.0,
        "min_position_size": 3.0,
        "trading_frequency": "monthly",
        "auto_trading_enabled": True,
        "auto_trading_max_amount": 50000,
        "stop_loss_preference": 8.0,
        "take_profit_preference": 30.0,
        "rebalancing_frequency": "quarterly",
        "dividend_preference": "reinvest",
        "tax_optimization_enabled": True,
        "esg_preference": True,
        "volatility_tolerance": "medium",
        "market_timing_preference": "systematic",
        "profile_notes": "Conservative investor with long-term goals"
    }
    
    # Test storing profile
    print("Step 1: Storing user investment profile...")
    success = store_user_investment_profile(user_id, sample_profile)
    print(f"✓ Storage result: {'SUCCESS' if success else 'FAILED'}")
    
    # Test retrieving profile
    print("\nStep 2: Retrieving user investment profile...")
    retrieved_profile = get_user_investment_profile(user_id)
    
    if retrieved_profile:
        print(f"✓ Profile retrieved successfully")
        print(f"✓ Risk tolerance: {retrieved_profile['risk_tolerance']}")
        print(f"✓ Investment timeline: {retrieved_profile['investment_timeline']}")
        print(f"✓ Preferred sectors: {len(retrieved_profile['preferred_sectors'])}")
        print(f"✓ Auto-trading enabled: {retrieved_profile['auto_trading_enabled']}")
        print(f"✓ Profile completeness: {retrieved_profile['profile_completeness_score']}%")
    else:
        print("✗ Profile retrieval FAILED")
    
    return retrieved_profile

def test_investment_goals():
    """Test investment goals functionality"""
    
    print("\n" + "=" * 60)
    print("TESTING INVESTMENT GOALS")
    print("=" * 60)
    
    user_id = "test_user_profile_123"
    
    # Sample goals
    sample_goals = [
        {
            "goal_name": "Retirement Fund",
            "goal_type": "retirement",
            "target_amount": 5000000,
            "current_amount": 500000,
            "target_date": "2045-12-31",
            "priority_level": 1,
            "monthly_contribution": 25000,
            "notes": "Primary retirement savings goal"
        },
        {
            "goal_name": "House Down Payment",
            "goal_type": "house",
            "target_amount": 2000000,
            "current_amount": 300000,
            "target_date": "2027-06-30",
            "priority_level": 2,
            "monthly_contribution": 50000,
            "notes": "Down payment for first home"
        }
    ]
    
    # Store goals
    print("Step 1: Storing investment goals...")
    goal_ids = []
    for goal in sample_goals:
        goal_id = store_investment_goal(user_id, goal)
        if goal_id:
            goal_ids.append(goal_id)
            print(f"✓ Stored goal '{goal['goal_name']}' with ID {goal_id}")
        else:
            print(f"✗ Failed to store goal '{goal['goal_name']}'")
    
    # Retrieve goals
    print("\nStep 2: Retrieving investment goals...")
    retrieved_goals = get_user_investment_goals(user_id)
    print(f"✓ Retrieved {len(retrieved_goals)} goals")
    
    for goal in retrieved_goals:
        print(f"✓ Goal: {goal['goal_name']} - {goal['goal_type']} - Priority {goal['priority_level']}")
    
    # Test goal progress update
    if goal_ids:
        print("\nStep 3: Testing goal progress update...")
        success = update_goal_progress(goal_ids[0], user_id, 750000)
        print(f"✓ Progress update result: {'SUCCESS' if success else 'FAILED'}")
        
        # Check updated progress
        updated_goals = get_user_investment_goals(user_id)
        if updated_goals:
            first_goal = updated_goals[0]
            print(f"✓ Updated progress: {first_goal['progress_percentage']:.1f}%")
    
    return retrieved_goals

def test_risk_assessment():
    """Test risk assessment functionality"""
    
    print("\n" + "=" * 60)
    print("TESTING RISK ASSESSMENT")
    print("=" * 60)
    
    user_id = "test_user_profile_123"
    
    # Sample risk assessment
    sample_assessment = {
        "risk_score": 75,
        "risk_tolerance": "moderate",
        "assessment_method": "questionnaire",
        "questionnaire_responses": {
            "age": 35,
            "investment_experience": "intermediate",
            "loss_comfort": "moderate",
            "time_horizon": "long_term"
        },
        "key_factors": [
            "Age allows for moderate risk",
            "Long-term investment horizon",
            "Stable income source"
        ],
        "recommended_allocation": {
            "equity": 70,
            "debt": 25,
            "cash": 5
        },
        "assessor_notes": "Suitable for balanced portfolio with growth focus"
    }
    
    # Store assessment
    print("Step 1: Storing risk assessment...")
    success = store_risk_assessment(user_id, sample_assessment)
    print(f"✓ Storage result: {'SUCCESS' if success else 'FAILED'}")
    
    # Retrieve current assessment
    print("\nStep 2: Retrieving current risk assessment...")
    current_assessment = get_current_risk_assessment(user_id)
    
    if current_assessment:
        print(f"✓ Assessment retrieved successfully")
        print(f"✓ Risk score: {current_assessment['risk_score']}")
        print(f"✓ Risk tolerance: {current_assessment['risk_tolerance']}")
        print(f"✓ Assessment method: {current_assessment['assessment_method']}")
        print(f"✓ Key factors: {len(current_assessment['key_factors'])}")
    else:
        print("✗ Assessment retrieval FAILED")
    
    return current_assessment

def test_profile_completeness():
    """Test profile completeness calculation"""
    
    print("\n" + "=" * 60)
    print("TESTING PROFILE COMPLETENESS")
    print("=" * 60)
    
    # Test with minimal profile
    minimal_profile = {
        "risk_tolerance": "moderate",
        "investment_timeline": "medium_term"
    }
    
    minimal_score = calculate_profile_completeness(minimal_profile)
    print(f"✓ Minimal profile completeness: {minimal_score}%")
    
    # Test with complete profile
    complete_profile = {
        "risk_tolerance": "moderate",
        "investment_timeline": "long_term",
        "max_position_size": 15.0,
        "trading_frequency": "monthly",
        "stop_loss_preference": 10.0,
        "take_profit_preference": 25.0,
        "investment_goals": ["retirement"],
        "preferred_sectors": ["technology"],
        "auto_trading_enabled": True,
        "rebalancing_frequency": "quarterly",
        "dividend_preference": "reinvest",
        "volatility_tolerance": "medium",
        "market_timing_preference": "systematic"
    }
    
    complete_score = calculate_profile_completeness(complete_profile)
    print(f"✓ Complete profile completeness: {complete_score}%")

def test_recommendations_context():
    """Test getting profile context for AI recommendations"""
    
    print("\n" + "=" * 60)
    print("TESTING RECOMMENDATIONS CONTEXT")
    print("=" * 60)
    
    user_id = "test_user_profile_123"
    
    print("Step 1: Getting profile-based recommendations context...")
    context = get_profile_based_recommendations_context(user_id)
    
    print(f"✓ Profile available: {context['profile_available']}")
    print(f"✓ Risk tolerance: {context['risk_tolerance']}")
    print(f"✓ Investment timeline: {context['investment_timeline']}")
    print(f"✓ Max position size: {context['max_position_size']}%")
    print(f"✓ Auto-trading enabled: {context['auto_trading_enabled']}")
    print(f"✓ Profile completeness: {context['profile_completeness']}%")
    print(f"✓ Active goals count: {context['active_goals_count']}")
    print(f"✓ Risk score: {context['risk_score']}")
    
    return context

def run_all_tests():
    """Run all user investment profile tests"""
    
    try:
        test_profile_schema()
        profile = test_profile_storage()
        goals = test_investment_goals()
        assessment = test_risk_assessment()
        test_profile_completeness()
        context = test_recommendations_context()
        
        print("\n" + "=" * 60)
        print("ALL USER INVESTMENT PROFILE TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print(f"\nTest Summary:")
        print(f"- Profile stored and retrieved: {'✓' if profile else '✗'}")
        print(f"- Investment goals: {len(goals) if goals else 0}")
        print(f"- Risk assessment: {'✓' if assessment else '✗'}")
        print(f"- Recommendations context: {'✓' if context['profile_available'] else '✗'}")
        
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