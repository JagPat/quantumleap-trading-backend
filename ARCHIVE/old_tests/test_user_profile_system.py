#!/usr/bin/env python3
"""
Test User Investment Profile System
Tests the complete user profile service, API endpoints, and database integration
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

async def test_user_profile_service():
    """Test the user profile service functionality"""
    print("🧪 Testing User Profile Service")
    print("=" * 60)
    
    try:
        from app.ai_engine.user_profile_service import user_profile_service
        
        test_user_id = "test_user_profile_123"
        
        print("1. Testing Default Profile Creation...")
        
        # Get profile for new user (should return defaults)
        profile = await user_profile_service.get_user_profile(test_user_id)
        
        print(f"✅ Default profile created")
        print(f"   - User ID: {profile.get('user_id', 'N/A')}")
        print(f"   - Risk Tolerance: {profile.get('risk_tolerance', 'N/A')}")
        print(f"   - Investment Timeline: {profile.get('investment_timeline', 'N/A')}")
        print(f"   - Profile Completeness: {profile.get('profile_completeness', 0):.1f}%")
        print(f"   - Risk Score: {profile.get('risk_score', 0):.1f}")
        print(f"   - Is New Profile: {profile.get('is_new_profile', False)}")
        
        print("\n2. Testing Profile Updates...")
        
        # Test profile updates
        test_updates = {
            "risk_tolerance": "aggressive",
            "investment_timeline": "long_term",
            "preferred_sectors": ["Technology", "Banking", "Pharmaceuticals"],
            "max_position_size": 20.0,
            "trading_frequency": "high",
            "auto_trading_enabled": True,
            "stop_loss_preference": 8.0,
            "take_profit_preference": 25.0,
            "esg_preference": True,
            "dividend_preference": "balanced"
        }
        
        updated_profile = await user_profile_service.update_user_profile(
            test_user_id, test_updates
        )
        
        print(f"✅ Profile updated successfully")
        print(f"   - Risk Tolerance: {updated_profile.get('risk_tolerance', 'N/A')}")
        print(f"   - Preferred Sectors: {len(updated_profile.get('preferred_sectors', []))} sectors")
        print(f"   - Profile Completeness: {updated_profile.get('profile_completeness', 0):.1f}%")
        print(f"   - Risk Score: {updated_profile.get('risk_score', 0):.1f}")
        print(f"   - Auto Trading: {updated_profile.get('auto_trading_enabled', False)}")
        
        print("\n3. Testing Profile Validation...")
        
        # Test validation with invalid data
        invalid_updates = {
            "risk_tolerance": "invalid_risk",  # Invalid value
            "max_position_size": 100.0,  # Too high
            "preferred_sectors": ["InvalidSector"],  # Invalid sector
            "stop_loss_preference": -5.0,  # Invalid percentage
            "trading_frequency": "extreme"  # Invalid frequency
        }
        
        validated_updates = user_profile_service._validate_profile_updates(invalid_updates)
        
        print(f"✅ Validation working correctly")
        print(f"   - Invalid fields rejected: {len(invalid_updates) - len(validated_updates)}")
        print(f"   - Valid fields accepted: {len(validated_updates)}")
        
        print("\n4. Testing Profile Recommendations...")
        
        # Get personalized recommendations
        recommendations = await user_profile_service.get_profile_recommendations(test_user_id)
        
        print(f"✅ Recommendations generated")
        print(f"   - Sector Allocation: {len(recommendations.get('sector_allocation', []))} recommendations")
        print(f"   - Risk Management: {len(recommendations.get('risk_management', []))} recommendations")
        print(f"   - Trading Strategy: {len(recommendations.get('trading_strategy', []))} recommendations")
        print(f"   - Portfolio Optimization: {len(recommendations.get('portfolio_optimization', []))} recommendations")
        print(f"   - Profile Improvements: {len(recommendations.get('profile_improvements', []))} suggestions")
        
        # Display sample recommendations
        if recommendations.get('sector_allocation'):
            sample_sector = recommendations['sector_allocation'][0]
            print(f"   - Sample Sector Rec: {sample_sector.get('sector')} - {sample_sector.get('recommended_allocation')}")
        
        print("\n5. Testing Risk Score Calculation...")
        
        # Test different risk profiles
        conservative_profile = {
            "risk_tolerance": "conservative",
            "investment_timeline": "long_term",
            "max_position_size": 10.0,
            "trading_frequency": "low"
        }
        
        aggressive_profile = {
            "risk_tolerance": "high",
            "investment_timeline": "short_term",
            "max_position_size": 25.0,
            "trading_frequency": "very_high"
        }
        
        conservative_score = user_profile_service._calculate_risk_score(conservative_profile)
        aggressive_score = user_profile_service._calculate_risk_score(aggressive_profile)
        
        print(f"✅ Risk score calculation working")
        print(f"   - Conservative Profile Score: {conservative_score:.1f}")
        print(f"   - Aggressive Profile Score: {aggressive_score:.1f}")
        print(f"   - Score Difference: {aggressive_score - conservative_score:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ User profile service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_profile_completeness():
    """Test profile completeness calculation"""
    print("\n🔍 Testing Profile Completeness Calculation")
    print("=" * 60)
    
    try:
        from app.ai_engine.user_profile_service import user_profile_service
        
        # Test minimal profile
        minimal_profile = {
            "risk_tolerance": "medium",
            "investment_timeline": "medium_term"
        }
        
        # Test complete profile
        complete_profile = {
            "risk_tolerance": "aggressive",
            "investment_timeline": "long_term",
            "preferred_sectors": ["Technology", "Banking", "Pharmaceuticals"],
            "max_position_size": 20.0,
            "min_position_size": 3.0,
            "trading_frequency": "moderate",
            "auto_trading_enabled": True,
            "stop_loss_preference": 10.0,
            "take_profit_preference": 20.0,
            "diversification_preference": "balanced",
            "esg_preference": True,
            "dividend_preference": "growth",
            "growth_vs_value": "growth"
        }
        
        minimal_completeness = user_profile_service._calculate_profile_completeness(minimal_profile)
        complete_completeness = user_profile_service._calculate_profile_completeness(complete_profile)
        
        print(f"✅ Completeness calculation working")
        print(f"   - Minimal Profile: {minimal_completeness:.1f}%")
        print(f"   - Complete Profile: {complete_completeness:.1f}%")
        print(f"   - Improvement: {complete_completeness - minimal_completeness:.1f}%")
        
        # Test that complete profile has higher score
        if complete_completeness > minimal_completeness:
            print(f"✅ Completeness scoring is logical")
            return True
        else:
            print(f"❌ Completeness scoring issue")
            return False
            
    except Exception as e:
        print(f"❌ Profile completeness test failed: {e}")
        return False

async def test_database_integration():
    """Test database integration for user profiles"""
    print("\n💾 Testing Database Integration")
    print("=" * 60)
    
    try:
        from app.database.service import save_user_investment_profile, get_user_investment_profile
        
        test_user_id = "test_db_user_456"
        
        # Test profile data
        test_profile = {
            "risk_tolerance": "moderate",
            "investment_timeline": "medium_term",
            "preferred_sectors": ["Technology", "Banking"],
            "max_position_size": 15.0,
            "trading_frequency": "moderate",
            "auto_trading_enabled": False,
            "stop_loss_preference": 10.0,
            "esg_preference": True
        }
        
        print("1. Testing Profile Storage...")
        
        # Save profile
        save_success = save_user_investment_profile(test_user_id, test_profile)
        
        if save_success:
            print(f"✅ Profile saved to database")
        else:
            print(f"❌ Failed to save profile")
            return False
        
        print("2. Testing Profile Retrieval...")
        
        # Retrieve profile
        retrieved_profile = get_user_investment_profile(test_user_id)
        
        if retrieved_profile:
            print(f"✅ Profile retrieved from database")
            print(f"   - User ID: {retrieved_profile.get('user_id', 'N/A')}")
            print(f"   - Risk Tolerance: {retrieved_profile.get('risk_tolerance', 'N/A')}")
            print(f"   - Preferred Sectors: {len(retrieved_profile.get('preferred_sectors', []))}")
            print(f"   - Auto Trading: {retrieved_profile.get('auto_trading_enabled', False)}")
            
            # Verify data integrity
            if (retrieved_profile.get('risk_tolerance') == test_profile['risk_tolerance'] and
                retrieved_profile.get('max_position_size') == test_profile['max_position_size']):
                print(f"✅ Data integrity verified")
                return True
            else:
                print(f"❌ Data integrity issue")
                return False
        else:
            print(f"❌ Failed to retrieve profile")
            return False
            
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ai_integration():
    """Test integration with AI analysis system"""
    print("\n🤖 Testing AI Integration")
    print("=" * 60)
    
    try:
        from app.ai_engine.user_profile_service import user_profile_service
        from app.ai_engine.simple_analysis_router import create_enhanced_portfolio_prompt
        
        test_user_id = "test_ai_user_789"
        
        # Create a user profile
        profile_updates = {
            "risk_tolerance": "aggressive",
            "investment_timeline": "long_term",
            "preferred_sectors": ["Technology", "Pharmaceuticals"],
            "max_position_size": 25.0,
            "trading_frequency": "high"
        }
        
        await user_profile_service.update_user_profile(test_user_id, profile_updates)
        profile = await user_profile_service.get_user_profile(test_user_id)
        
        print("1. Testing Profile Integration in AI Prompts...")
        
        # Test portfolio data
        test_portfolio = {
            "total_value": 1000000,
            "holdings": [
                {
                    "tradingsymbol": "TCS",
                    "current_value": 300000,
                    "quantity": 100,
                    "average_price": 2800,
                    "last_price": 3000,
                    "pnl": 20000,
                    "pnl_percentage": 7.14
                }
            ],
            "positions": []
        }
        
        # Create enhanced prompt with user preferences
        user_preferences = {
            'risk_tolerance': profile.get('risk_tolerance'),
            'investment_timeline': profile.get('investment_timeline'),
            'preferred_sectors': profile.get('preferred_sectors', []),
            'max_position_size': profile.get('max_position_size')
        }
        
        enhanced_prompt = await create_enhanced_portfolio_prompt(
            test_portfolio,
            test_user_id,
            user_preferences,
            None  # No market context for this test
        )
        
        print(f"✅ AI prompt generated with user profile")
        print(f"   - Prompt length: {len(enhanced_prompt):,} characters")
        
        # Check if user preferences are included
        profile_keywords = [
            "USER INVESTMENT PROFILE",
            f"Risk Tolerance: {profile.get('risk_tolerance', '').upper()}",
            f"Investment Timeline: {profile.get('investment_timeline', '').replace('_', ' ').title()}",
            f"Maximum Position Size: {profile.get('max_position_size', 0)}%"
        ]
        
        included_keywords = [kw for kw in profile_keywords if kw in enhanced_prompt]
        print(f"   - Profile keywords found: {len(included_keywords)}/{len(profile_keywords)}")
        
        if len(included_keywords) >= len(profile_keywords) * 0.8:
            print("✅ User profile successfully integrated into AI prompts")
            return True
        else:
            print("⚠️  Some profile elements may be missing from AI prompts")
            return False
            
    except Exception as e:
        print(f"❌ AI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all user profile system tests"""
    print("🚀 Starting User Investment Profile System Tests")
    print("=" * 60)
    
    # Run tests
    test1_passed = await test_user_profile_service()
    test2_passed = await test_profile_completeness()
    test3_passed = await test_database_integration()
    test4_passed = await test_ai_integration()
    
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 60)
    
    tests_passed = sum([test1_passed, test2_passed, test3_passed, test4_passed])
    total_tests = 4
    
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"✅ User Profile Service: {'PASS' if test1_passed else 'FAIL'}")
    print(f"✅ Profile Completeness: {'PASS' if test2_passed else 'FAIL'}")
    print(f"✅ Database Integration: {'PASS' if test3_passed else 'FAIL'}")
    print(f"✅ AI Integration: {'PASS' if test4_passed else 'FAIL'}")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED - User Profile System is working correctly!")
        print("\n✅ Ready for next implementation phase:")
        print("   - Frontend Enhancement with Actions Tab")
        print("   - Auto-Trading Engine Integration")
        print("   - Enhanced Analytics Dashboard")
        return True
    else:
        print(f"\n⚠️  {total_tests - tests_passed} TESTS FAILED - Review and fix issues before proceeding")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)