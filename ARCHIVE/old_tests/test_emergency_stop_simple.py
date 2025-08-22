"""
Simple Emergency Stop System Test
Basic test without external dependencies
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_emergency_stop_basic():
    """Basic test of emergency stop system"""
    print("Testing Emergency Stop System...")
    
    try:
        # Import the emergency stop system
        from trading_engine.emergency_stop import (
            EmergencyStopSystem,
            EmergencyStopRequest,
            EmergencyStopReason,
            EmergencyStopScope
        )
        
        print("✓ Emergency stop imports successful")
        
        # Create emergency stop system
        stop_system = EmergencyStopSystem()
        print("✓ Emergency stop system created")
        
        # Test creating a request
        request = EmergencyStopRequest(
            user_id="test_user",
            reason=EmergencyStopReason.USER_INITIATED,
            scope=EmergencyStopScope.USER,
            message="Test emergency stop"
        )
        print("✓ Emergency stop request created")
        
        # Test history functionality
        history = stop_system.get_stop_history(user_id="test_user")
        print(f"✓ History retrieved: {len(history)} entries")
        
        # Test active stops
        active_stops = stop_system.get_active_stops()
        print(f"✓ Active stops retrieved: {len(active_stops)} entries")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

async def test_emergency_stop_enums():
    """Test emergency stop enums"""
    print("\nTesting Emergency Stop Enums...")
    
    try:
        from trading_engine.emergency_stop import EmergencyStopReason, EmergencyStopScope
        
        # Test reasons
        reasons = [
            EmergencyStopReason.USER_INITIATED,
            EmergencyStopReason.RISK_VIOLATION,
            EmergencyStopReason.SYSTEM_ERROR,
            EmergencyStopReason.MARKET_CONDITION
        ]
        print(f"✓ Emergency stop reasons: {[r.value for r in reasons]}")
        
        # Test scopes
        scopes = [
            EmergencyStopScope.USER,
            EmergencyStopScope.STRATEGY,
            EmergencyStopScope.SYMBOL,
            EmergencyStopScope.SYSTEM
        ]
        print(f"✓ Emergency stop scopes: {[s.value for s in scopes]}")
        
        print("✓ All enum tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Enum test error: {e}")
        return False

async def test_emergency_stop_models():
    """Test emergency stop data models"""
    print("\nTesting Emergency Stop Models...")
    
    try:
        from trading_engine.emergency_stop import (
            EmergencyStopRequest,
            EmergencyStopResult,
            EmergencyStopReason,
            EmergencyStopScope
        )
        from datetime import datetime
        
        # Test request model
        request = EmergencyStopRequest(
            user_id="test_user_123",
            reason=EmergencyStopReason.USER_INITIATED,
            scope=EmergencyStopScope.USER,
            message="Test message",
            initiated_by="test_user_123"
        )
        
        print(f"✓ Request created: {request.user_id}, {request.reason.value}")
        
        # Test result model
        result = EmergencyStopResult(
            success=True,
            request=request,
            orders_cancelled=5,
            strategies_paused=2,
            positions_closed=1
        )
        
        print(f"✓ Result created: success={result.success}, orders={result.orders_cancelled}")
        
        print("✓ All model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test error: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("EMERGENCY STOP SYSTEM TESTS")
    print("=" * 50)
    
    tests = [
        test_emergency_stop_basic,
        test_emergency_stop_enums,
        test_emergency_stop_models
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