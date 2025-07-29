#!/usr/bin/env python3
"""
Simple User Profile Database Test
Tests basic database operations for user profiles
"""
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def test_simple_profile_operations():
    """Test basic profile database operations"""
    print("🧪 Testing Simple User Profile Database Operations")
    print("=" * 60)
    
    try:
        from app.database.service import save_user_investment_profile, get_user_investment_profile
        
        test_user_id = "test_simple_user"
        
        # Test with database-compatible values
        test_profile = {
            "risk_tolerance": "moderate",  # Valid: conservative, moderate, aggressive
            "investment_timeline": "long_term",  # Valid: short_term, medium_term, long_term
            "preferred_sectors": ["Technology", "Banking"],
            "max_position_size": 15.0,
            "min_position_size": 3.0,
            "trading_frequency": "monthly",  # Valid: daily, weekly, monthly, quarterly
            "auto_trading_enabled": False,
            "stop_loss_preference": 10.0,
            "take_profit_preference": 20.0,
            "esg_preference": True,
            "dividend_preference": "reinvest"  # Valid: reinvest, payout, balanced
        }
        
        print("1. Testing Profile Save...")
        
        # Save profile
        save_success = save_user_investment_profile(test_user_id, test_profile)
        
        if save_success:
            print("✅ Profile saved successfully")
        else:
            print("❌ Failed to save profile")
            return False
        
        print("2. Testing Profile Retrieval...")
        
        # Retrieve profile
        retrieved_profile = get_user_investment_profile(test_user_id)
        
        if retrieved_profile:
            print("✅ Profile retrieved successfully")
            print(f"   - User ID: {retrieved_profile.get('user_id')}")
            print(f"   - Risk Tolerance: {retrieved_profile.get('risk_tolerance')}")
            print(f"   - Investment Timeline: {retrieved_profile.get('investment_timeline')}")
            print(f"   - Trading Frequency: {retrieved_profile.get('trading_frequency')}")
            print(f"   - Preferred Sectors: {len(retrieved_profile.get('preferred_sectors', []))}")
            print(f"   - Auto Trading: {retrieved_profile.get('auto_trading_enabled')}")
            print(f"   - ESG Preference: {retrieved_profile.get('esg_preference')}")
            
            # Verify key data
            if (retrieved_profile.get('risk_tolerance') == test_profile['risk_tolerance'] and
                retrieved_profile.get('trading_frequency') == test_profile['trading_frequency']):
                print("✅ Data integrity verified")
                return True
            else:
                print("❌ Data integrity issue")
                print(f"   Expected risk: {test_profile['risk_tolerance']}, Got: {retrieved_profile.get('risk_tolerance')}")
                print(f"   Expected frequency: {test_profile['trading_frequency']}, Got: {retrieved_profile.get('trading_frequency')}")
                return False
        else:
            print("❌ Failed to retrieve profile")
            return False
            
    except Exception as e:
        print(f"❌ Simple profile test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_profile_service_integration():
    """Test user profile service with database"""
    print("\n🔧 Testing User Profile Service Integration")
    print("=" * 60)
    
    try:
        import asyncio
        from app.ai_engine.user_profile_service import user_profile_service
        
        async def run_service_test():
            test_user_id = "test_service_user"
            
            print("1. Testing Service Profile Creation...")
            
            # Get default profile
            profile = await user_profile_service.get_user_profile(test_user_id)
            print(f"✅ Default profile created")
            print(f"   - Risk Tolerance: {profile.get('risk_tolerance')}")
            print(f"   - Trading Frequency: {profile.get('trading_frequency')}")
            
            print("2. Testing Service Profile Update...")
            
            # Update with valid values
            updates = {
                "risk_tolerance": "aggressive",
                "investment_timeline": "long_term",
                "preferred_sectors": ["Technology", "Pharmaceuticals"],
                "trading_frequency": "weekly",  # This should be valid
                "max_position_size": 20.0,
                "auto_trading_enabled": True
            }
            
            updated_profile = await user_profile_service.update_user_profile(test_user_id, updates)
            
            print(f"✅ Profile updated via service")
            print(f"   - Risk Tolerance: {updated_profile.get('risk_tolerance')}")
            print(f"   - Trading Frequency: {updated_profile.get('trading_frequency')}")
            print(f"   - Preferred Sectors: {len(updated_profile.get('preferred_sectors', []))}")
            print(f"   - Profile Completeness: {updated_profile.get('profile_completeness', 0):.1f}%")
            
            # Verify the update worked
            if updated_profile.get('risk_tolerance') == 'aggressive':
                print("✅ Service integration working")
                return True
            else:
                print("❌ Service integration issue")
                return False
        
        return asyncio.run(run_service_test())
        
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run simple database tests"""
    print("🚀 Starting Simple User Profile Database Tests")
    print("=" * 60)
    
    test1_passed = test_simple_profile_operations()
    test2_passed = test_user_profile_service_integration()
    
    print("\n" + "=" * 60)
    print("🏁 SIMPLE TEST RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("🎉 ALL SIMPLE TESTS PASSED!")
        print("✅ Database operations working")
        print("✅ Service integration working")
        print("✅ Ready for full system testing")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        print(f"✅ Database Operations: {'PASS' if test1_passed else 'FAIL'}")
        print(f"✅ Service Integration: {'PASS' if test2_passed else 'FAIL'}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)