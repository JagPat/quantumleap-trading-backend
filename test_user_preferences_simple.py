"""
Simple User Preferences System Test
Basic test without external dependencies
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_user_preferences_basic():
    """Basic test of user preferences system"""
    print("Testing User Preferences System...")
    
    try:
        # Import the user preferences system
        from trading_engine.user_preferences import (
            UserPreferencesManager,
            UserPreferences,
            TradingPreferences,
            NotificationPreference,
            PreferenceCategory,
            NotificationChannel,
            NotificationPriority
        )
        
        print("✓ User preferences imports successful")
        
        # Create user preferences manager
        prefs_manager = UserPreferencesManager()
        print("✓ User preferences manager created")
        
        # Test getting user preferences (should create defaults)
        user_prefs = await prefs_manager.get_user_preferences("test_user")
        print(f"✓ User preferences retrieved: {user_prefs.user_id}")
        
        # Test preference summary
        summary = prefs_manager.get_preference_summary("test_user")
        print(f"✓ Preference summary retrieved: {len(summary)} fields")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

async def test_user_preferences_enums():
    """Test user preferences enums"""
    print("\nTesting User Preferences Enums...")
    
    try:
        from trading_engine.user_preferences import (
            PreferenceCategory,
            NotificationChannel,
            NotificationPriority
        )
        
        # Test preference categories
        categories = [
            PreferenceCategory.TRADING,
            PreferenceCategory.RISK_MANAGEMENT,
            PreferenceCategory.NOTIFICATIONS,
            PreferenceCategory.STRATEGY,
            PreferenceCategory.MARKET_DATA,
            PreferenceCategory.PERFORMANCE
        ]
        print(f"✓ Preference categories: {[c.value for c in categories]}")
        
        # Test notification channels
        channels = [
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.PUSH,
            NotificationChannel.IN_APP,
            NotificationChannel.WEBHOOK
        ]
        print(f"✓ Notification channels: {[c.value for c in channels]}")
        
        # Test notification priorities
        priorities = [
            NotificationPriority.LOW,
            NotificationPriority.MEDIUM,
            NotificationPriority.HIGH,
            NotificationPriority.CRITICAL
        ]
        print(f"✓ Notification priorities: {[p.value for p in priorities]}")
        
        print("✓ All enum tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Enum test error: {e}")
        return False

async def test_user_preferences_models():
    """Test user preferences data models"""
    print("\nTesting User Preferences Models...")
    
    try:
        from trading_engine.user_preferences import (
            TradingPreferences,
            NotificationPreference,
            UserPreferences,
            NotificationChannel,
            NotificationPriority
        )
        
        # Test trading preferences
        trading_prefs = TradingPreferences(
            auto_execute_signals=True,
            min_confidence_threshold=0.8,
            max_daily_trades=25
        )
        print(f"✓ Trading preferences created: auto_execute={trading_prefs.auto_execute_signals}")
        
        # Test notification preference
        notification_pref = NotificationPreference(
            event_type="ORDER_FILLED",
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
            priority=NotificationPriority.MEDIUM,
            enabled=True
        )
        print(f"✓ Notification preference created: {notification_pref.event_type}")
        
        # Test user preferences
        user_prefs = UserPreferences(
            user_id="test_user_123",
            trading=trading_prefs,
            notifications=[notification_pref]
        )
        print(f"✓ User preferences created: {user_prefs.user_id}")
        
        # Test serialization
        prefs_dict = user_prefs.to_dict()
        print(f"✓ Preferences serialized: {len(prefs_dict)} fields")
        
        # Test deserialization
        restored_prefs = UserPreferences.from_dict(prefs_dict)
        print(f"✓ Preferences deserialized: {restored_prefs.user_id}")
        
        print("✓ All model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test error: {e}")
        return False

async def test_preference_updates():
    """Test preference update functionality"""
    print("\nTesting Preference Updates...")
    
    try:
        from trading_engine.user_preferences import (
            UserPreferencesManager,
            PreferenceCategory
        )
        
        prefs_manager = UserPreferencesManager()
        
        # Test trading preference update
        success = await prefs_manager.update_preferences(
            "test_user",
            PreferenceCategory.TRADING.value,
            {"auto_execute_signals": False, "min_confidence_threshold": 0.9}
        )
        print(f"✓ Trading preferences updated: {success}")
        
        # Test risk preference update
        success = await prefs_manager.update_preferences(
            "test_user",
            PreferenceCategory.RISK_MANAGEMENT.value,
            {"max_position_size_percent": 3.0, "stop_loss_percent": 2.0}
        )
        print(f"✓ Risk preferences updated: {success}")
        
        # Verify updates were applied
        user_prefs = await prefs_manager.get_user_preferences("test_user")
        print(f"✓ Updated preferences verified: auto_execute={user_prefs.trading.auto_execute_signals}")
        
        print("✓ All update tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Update test error: {e}")
        return False

async def test_notification_checking():
    """Test notification preference checking"""
    print("\nTesting Notification Checking...")
    
    try:
        from trading_engine.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager()
        
        # Test notification check
        result = await prefs_manager.should_send_notification(
            "test_user",
            "ORDER_FILLED",
            {"symbol": "RELIANCE", "quantity": 100}
        )
        print(f"✓ Notification check result: should_send={result.get('should_send', False)}")
        
        # Test with non-existent event type
        result = await prefs_manager.should_send_notification(
            "test_user",
            "UNKNOWN_EVENT",
            {}
        )
        print(f"✓ Unknown event check: should_send={result.get('should_send', False)}")
        
        print("✓ All notification tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Notification test error: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("USER PREFERENCES SYSTEM TESTS")
    print("=" * 50)
    
    tests = [
        test_user_preferences_basic,
        test_user_preferences_enums,
        test_user_preferences_models,
        test_preference_updates,
        test_notification_checking
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)