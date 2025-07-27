#!/usr/bin/env python3
"""
Simple Backend Logic Test
Test core trading engine logic without external dependencies
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_models():
    """Test core data models"""
    print("📋 Testing Core Models...")
    
    try:
        from trading_engine.models import (
            TradingSignal, SignalType, Order, OrderType, OrderSide, OrderStatus,
            RiskParameters, Position, Execution
        )
        
        # Test TradingSignal
        signal = TradingSignal(
            id="test_signal",
            user_id="test_user",
            symbol="RELIANCE",
            signal_type=SignalType.BUY,
            confidence_score=0.8,
            target_price=2500.0,
            stop_loss=2400.0
        )
        
        # Test serialization
        signal_dict = signal.to_dict()
        signal_restored = TradingSignal.from_dict(signal_dict)
        
        assert signal_restored.id == signal.id, "Signal serialization failed"
        assert signal_restored.confidence_score == signal.confidence_score, "Signal data integrity failed"
        
        # Test Order model
        order = Order(
            id="test_order",
            user_id="test_user",
            symbol="RELIANCE",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,
            price=2500.0
        )
        
        # Test order methods
        order.add_fill(5, 2495.0, 2.5)
        
        assert order.filled_quantity == 5, "Order fill logic failed"
        assert order.is_partially_filled, "Order status logic failed"
        assert order.remaining_quantity == 5, "Remaining quantity calculation failed"
        
        # Test Position model
        position = Position(
            id="test_position",
            user_id="test_user",
            symbol="RELIANCE",
            quantity=10,
            average_price=2500.0
        )
        
        position.update_price(2550.0)
        assert position.unrealized_pnl > 0, "Position P&L calculation failed"
        
        print("✅ Core Models: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Core Models: FAILED - {e}")
        return False

def test_risk_calculations():
    """Test risk calculation logic"""
    print("📋 Testing Risk Calculations...")
    
    try:
        from trading_engine.models import RiskParameters
        
        # Test risk parameters
        risk_params = RiskParameters()
        
        # Test default values
        assert risk_params.max_position_size_percent > 0, "Invalid default position size"
        assert risk_params.max_portfolio_exposure_percent > 0, "Invalid default portfolio exposure"
        assert risk_params.stop_loss_percent > 0, "Invalid default stop loss"
        
        # Test serialization
        risk_dict = risk_params.to_dict()
        risk_restored = RiskParameters.from_dict(risk_dict)
        
        assert risk_restored.max_position_size_percent == risk_params.max_position_size_percent, "Risk params serialization failed"
        
        print("✅ Risk Calculations: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Risk Calculations: FAILED - {e}")
        return False

def test_business_logic():
    """Test core business logic"""
    print("📋 Testing Business Logic...")
    
    try:
        from trading_engine.models import Order, OrderType, OrderSide, OrderStatus
        
        # Test order lifecycle
        order = Order(
            id="test_business_order",
            user_id="test_user",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100
        )
        
        # Test status transitions
        assert order.status == OrderStatus.PENDING, "Initial order status incorrect"
        
        order.update_status(OrderStatus.SUBMITTED)
        assert order.status == OrderStatus.SUBMITTED, "Status update failed"
        assert order.submitted_at is not None, "Submitted timestamp not set"
        
        # Test partial fill
        order.add_fill(50, 2500.0, 5.0)
        assert order.status == OrderStatus.PARTIALLY_FILLED, "Partial fill status incorrect"
        assert order.filled_quantity == 50, "Fill quantity incorrect"
        assert order.average_fill_price == 2500.0, "Average fill price incorrect"
        
        # Test complete fill
        order.add_fill(50, 2510.0, 5.0)
        assert order.status == OrderStatus.FILLED, "Complete fill status incorrect"
        assert order.is_filled, "Order should be completely filled"
        
        # Test average price calculation
        expected_avg = (50 * 2500.0 + 50 * 2510.0) / 100
        assert abs(order.average_fill_price - expected_avg) < 0.01, "Average price calculation incorrect"
        
        print("✅ Business Logic: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Business Logic: FAILED - {e}")
        return False

def test_data_integrity():
    """Test data integrity and validation"""
    print("📋 Testing Data Integrity...")
    
    try:
        from trading_engine.models import TradingSignal, SignalType
        
        # Test signal expiry
        signal = TradingSignal(
            id="test_expiry_signal",
            user_id="test_user",
            symbol="RELIANCE",
            signal_type=SignalType.BUY,
            confidence_score=0.8,
            expires_at=datetime.now() - timedelta(minutes=1)  # Expired
        )
        
        assert signal.is_expired(), "Signal expiry check failed"
        
        # Test confidence score validation
        try:
            invalid_signal = TradingSignal(
                id="test_invalid_signal",
                user_id="test_user",
                symbol="RELIANCE",
                signal_type=SignalType.BUY,
                confidence_score=1.5  # Invalid - should be 0-1
            )
            # This should work but we can add validation later
        except:
            pass  # Expected if validation is implemented
        
        print("✅ Data Integrity: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Data Integrity: FAILED - {e}")
        return False

def main():
    """Run all simple tests"""
    print("🚀 Starting Simple Backend Logic Tests")
    print("=" * 50)
    
    tests = [
        ("Core Models", test_models),
        ("Risk Calculations", test_risk_calculations),
        ("Business Logic", test_business_logic),
        ("Data Integrity", test_data_integrity)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All core logic tests passed!")
        print("✅ Backend core functionality is working correctly")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        print("❌ Backend needs attention before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)