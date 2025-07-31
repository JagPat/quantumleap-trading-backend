"""
Simple Manual Override System Test
Basic test without external dependencies
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_manual_override_basic():
    """Basic test of manual override system"""
    print("Testing Manual Override System...")
    
    try:
        # Import the manual override system
        from trading_engine.manual_override import (
            ManualOverrideSystem,
            ManualOverrideRequest,
            OverrideType,
            OverrideReason
        )
        
        print("✓ Manual override imports successful")
        
        # Create manual override system
        override_system = ManualOverrideSystem()
        print("✓ Manual override system created")
        
        # Test creating a request
        request = ManualOverrideRequest(
            id="test_override_123",
            user_id="test_user",
            override_type=OverrideType.MANUAL_ORDER,
            reason=OverrideReason.USER_DECISION,
            description="Test manual override",
            parameters={
                'symbol': 'RELIANCE',
                'side': 'BUY',
                'quantity': 10,
                'order_type': 'MARKET'
            },
            initiated_by="test_user"
        )
        print("✓ Manual override request created")
        
        # Test history functionality
        history = override_system.get_override_history(user_id="test_user")
        print(f"✓ History retrieved: {len(history)} entries")
        
        # Test pending overrides
        pending = override_system.get_pending_overrides(user_id="test_user")
        print(f"✓ Pending overrides retrieved: {len(pending)} entries")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

async def test_manual_override_enums():
    """Test manual override enums"""
    print("\nTesting Manual Override Enums...")
    
    try:
        from trading_engine.manual_override import OverrideType, OverrideReason
        
        # Test override types
        override_types = [
            OverrideType.MANUAL_ORDER,
            OverrideType.STRATEGY_CONTROL,
            OverrideType.POSITION_CLOSURE,
            OverrideType.RISK_ADJUSTMENT,
            OverrideType.SIGNAL_OVERRIDE
        ]
        print(f"✓ Override types: {[t.value for t in override_types]}")
        
        # Test override reasons
        reasons = [
            OverrideReason.USER_DECISION,
            OverrideReason.MARKET_OPPORTUNITY,
            OverrideReason.RISK_MANAGEMENT,
            OverrideReason.TECHNICAL_ISSUE,
            OverrideReason.NEWS_EVENT,
            OverrideReason.STRATEGY_ADJUSTMENT
        ]
        print(f"✓ Override reasons: {[r.value for r in reasons]}")
        
        print("✓ All enum tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Enum test error: {e}")
        return False

async def test_manual_override_models():
    """Test manual override data models"""
    print("\nTesting Manual Override Models...")
    
    try:
        from trading_engine.manual_override import (
            ManualOverrideRequest,
            ManualOverrideResult,
            OverrideType,
            OverrideReason
        )
        from datetime import datetime
        
        # Test request model
        request = ManualOverrideRequest(
            id="test_override_456",
            user_id="test_user_123",
            override_type=OverrideType.STRATEGY_CONTROL,
            reason=OverrideReason.USER_DECISION,
            description="Test strategy control",
            parameters={
                'strategy_id': 'strategy_123',
                'action': 'pause'
            },
            initiated_by="test_user_123"
        )
        
        print(f"✓ Request created: {request.user_id}, {request.override_type.value}")
        
        # Test result model
        result = ManualOverrideResult(
            success=True,
            request=request,
            actions_taken=["Strategy paused successfully"],
            warnings=[],
            errors=[],
            risk_validation={'approved': True},
            execution_time_ms=125.5
        )
        
        print(f"✓ Result created: success={result.success}, actions={len(result.actions_taken)}")
        
        print("✓ All model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test error: {e}")
        return False

async def test_convenience_methods():
    """Test convenience methods"""
    print("\nTesting Convenience Methods...")
    
    try:
        from trading_engine.manual_override import ManualOverrideSystem
        
        override_system = ManualOverrideSystem()
        
        # Test method signatures (without actual execution)
        print("✓ place_manual_order method available")
        print("✓ control_strategy method available")  
        print("✓ close_position_manually method available")
        
        # Test that methods exist and are callable
        assert hasattr(override_system, 'place_manual_order')
        assert callable(getattr(override_system, 'place_manual_order'))
        
        assert hasattr(override_system, 'control_strategy')
        assert callable(getattr(override_system, 'control_strategy'))
        
        assert hasattr(override_system, 'close_position_manually')
        assert callable(getattr(override_system, 'close_position_manually'))
        
        print("✓ All convenience method tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Convenience method test error: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("MANUAL OVERRIDE SYSTEM TESTS")
    print("=" * 50)
    
    tests = [
        test_manual_override_basic,
        test_manual_override_enums,
        test_manual_override_models,
        test_convenience_methods
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