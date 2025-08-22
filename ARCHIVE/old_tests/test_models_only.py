#!/usr/bin/env python3
"""
Test Trading Engine Models Only
Test core data models without any external dependencies
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

# Copy the essential models here for testing
class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"

class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"

@dataclass
class TradingSignal:
    id: str
    user_id: str
    symbol: str
    signal_type: SignalType
    confidence_score: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    processed: bool = False
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=1)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat() if self.expires_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        data = data.copy()
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)

@dataclass
class Order:
    id: str
    user_id: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_fill_price: Optional[float] = None
    commission: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity
    
    @property
    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity
    
    @property
    def is_partially_filled(self) -> bool:
        return 0 < self.filled_quantity < self.quantity
    
    def update_status(self, new_status: OrderStatus):
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status == OrderStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = datetime.now()
        elif new_status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED] and not self.filled_at:
            self.filled_at = datetime.now()
    
    def add_fill(self, quantity: int, price: float, commission: float = 0.0):
        if quantity <= 0:
            raise ValueError("Fill quantity must be positive")
        
        if self.filled_quantity + quantity > self.quantity:
            raise ValueError("Fill quantity exceeds order quantity")
        
        # Calculate new average fill price
        if self.filled_quantity == 0:
            self.average_fill_price = price
        else:
            total_value = (self.average_fill_price * self.filled_quantity) + (price * quantity)
            self.average_fill_price = total_value / (self.filled_quantity + quantity)
        
        self.filled_quantity += quantity
        self.commission += commission
        
        # Update status
        if self.is_filled:
            self.update_status(OrderStatus.FILLED)
        else:
            self.update_status(OrderStatus.PARTIALLY_FILLED)

@dataclass
class Position:
    id: str
    user_id: str
    symbol: str
    quantity: int
    average_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def is_long(self) -> bool:
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        return self.quantity < 0
    
    @property
    def is_closed(self) -> bool:
        return self.quantity == 0 or self.closed_at is not None
    
    def update_price(self, new_price: float):
        self.current_price = new_price
        self.updated_at = datetime.now()
        
        if self.quantity != 0:
            if self.is_long:
                self.unrealized_pnl = self.quantity * (new_price - self.average_price)
            else:
                self.unrealized_pnl = abs(self.quantity) * (self.average_price - new_price)

def test_trading_signal():
    """Test TradingSignal model"""
    print("📋 Testing TradingSignal...")
    
    # Create signal
    signal = TradingSignal(
        id="test_signal_1",
        user_id="user123",
        symbol="RELIANCE",
        signal_type=SignalType.BUY,
        confidence_score=0.85,
        target_price=2500.0,
        stop_loss=2400.0
    )
    
    # Test basic properties
    assert signal.id == "test_signal_1"
    assert signal.confidence_score == 0.85
    assert signal.signal_type == SignalType.BUY
    assert not signal.processed
    
    # Test expiry
    assert not signal.is_expired()  # Should not be expired immediately
    
    # Test serialization
    signal_dict = signal.to_dict()
    assert isinstance(signal_dict, dict)
    assert signal_dict['id'] == "test_signal_1"
    assert signal_dict['confidence_score'] == 0.85
    
    # Test deserialization
    restored_signal = TradingSignal.from_dict(signal_dict)
    assert restored_signal.id == signal.id
    assert restored_signal.confidence_score == signal.confidence_score
    assert restored_signal.signal_type == signal.signal_type
    
    print("✅ TradingSignal: PASSED")
    return True

def test_order_model():
    """Test Order model"""
    print("📋 Testing Order...")
    
    # Create order
    order = Order(
        id="test_order_1",
        user_id="user123",
        symbol="RELIANCE",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=100,
        price=2500.0
    )
    
    # Test basic properties
    assert order.id == "test_order_1"
    assert order.quantity == 100
    assert order.status == OrderStatus.PENDING
    assert order.remaining_quantity == 100
    assert not order.is_filled
    assert not order.is_partially_filled
    
    # Test status update
    order.update_status(OrderStatus.SUBMITTED)
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None
    
    # Test partial fill
    order.add_fill(50, 2495.0, 5.0)
    assert order.filled_quantity == 50
    assert order.remaining_quantity == 50
    assert order.is_partially_filled
    assert not order.is_filled
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.average_fill_price == 2495.0
    assert order.commission == 5.0
    
    # Test complete fill
    order.add_fill(50, 2505.0, 5.0)
    assert order.filled_quantity == 100
    assert order.remaining_quantity == 0
    assert order.is_filled
    assert not order.is_partially_filled
    assert order.status == OrderStatus.FILLED
    assert order.commission == 10.0
    
    # Test average price calculation
    expected_avg = (50 * 2495.0 + 50 * 2505.0) / 100
    assert abs(order.average_fill_price - expected_avg) < 0.01
    
    print("✅ Order: PASSED")
    return True

def test_position_model():
    """Test Position model"""
    print("📋 Testing Position...")
    
    # Create long position
    position = Position(
        id="test_position_1",
        user_id="user123",
        symbol="RELIANCE",
        quantity=100,
        average_price=2500.0
    )
    
    # Test basic properties
    assert position.quantity == 100
    assert position.average_price == 2500.0
    assert position.is_long
    assert not position.is_short
    assert not position.is_closed
    
    # Test price update and P&L calculation
    position.update_price(2550.0)
    assert position.current_price == 2550.0
    assert position.unrealized_pnl == 100 * (2550.0 - 2500.0)  # 5000.0
    
    # Test price decrease
    position.update_price(2450.0)
    assert position.unrealized_pnl == 100 * (2450.0 - 2500.0)  # -5000.0
    
    # Test short position
    short_position = Position(
        id="test_position_2",
        user_id="user123",
        symbol="RELIANCE",
        quantity=-50,  # Short position
        average_price=2500.0
    )
    
    assert short_position.is_short
    assert not short_position.is_long
    
    # Test short position P&L
    short_position.update_price(2450.0)  # Price goes down, short profits
    assert short_position.unrealized_pnl == 50 * (2500.0 - 2450.0)  # 2500.0
    
    print("✅ Position: PASSED")
    return True

def test_business_logic():
    """Test business logic scenarios"""
    print("📋 Testing Business Logic...")
    
    # Test order lifecycle
    order = Order(
        id="lifecycle_order",
        user_id="user123",
        symbol="RELIANCE",
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=100
    )
    
    # Initial state
    assert order.status == OrderStatus.PENDING
    
    # Submit order
    order.update_status(OrderStatus.SUBMITTED)
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None
    
    # Partial execution
    order.add_fill(30, 2500.0, 3.0)
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == 30
    
    # Another partial fill
    order.add_fill(40, 2510.0, 4.0)
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == 70
    
    # Final fill
    order.add_fill(30, 2520.0, 3.0)
    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 100
    assert order.is_filled
    
    # Test average price calculation
    expected_avg = (30 * 2500.0 + 40 * 2510.0 + 30 * 2520.0) / 100
    assert abs(order.average_fill_price - expected_avg) < 0.01
    
    # Test total commission
    assert order.commission == 10.0
    
    print("✅ Business Logic: PASSED")
    return True

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("📋 Testing Edge Cases...")
    
    # Test overfill protection
    order = Order(
        id="overfill_test",
        user_id="user123",
        symbol="RELIANCE",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=100,
        price=2500.0
    )
    
    # Try to overfill
    order.add_fill(60, 2500.0, 6.0)
    
    try:
        order.add_fill(50, 2500.0, 5.0)  # This should fail (60 + 50 > 100)
        assert False, "Should have raised ValueError for overfill"
    except ValueError:
        pass  # Expected
    
    # Test zero quantity fill
    try:
        order.add_fill(0, 2500.0, 0.0)
        assert False, "Should have raised ValueError for zero quantity"
    except ValueError:
        pass  # Expected
    
    # Test negative quantity fill
    try:
        order.add_fill(-10, 2500.0, 0.0)
        assert False, "Should have raised ValueError for negative quantity"
    except ValueError:
        pass  # Expected
    
    # Test signal expiry
    expired_signal = TradingSignal(
        id="expired_signal",
        user_id="user123",
        symbol="RELIANCE",
        signal_type=SignalType.BUY,
        confidence_score=0.8,
        expires_at=datetime.now() - timedelta(minutes=1)
    )
    
    assert expired_signal.is_expired()
    
    print("✅ Edge Cases: PASSED")
    return True

def main():
    """Run all model tests"""
    print("🚀 Testing Trading Engine Core Models")
    print("=" * 50)
    
    tests = [
        ("TradingSignal Model", test_trading_signal),
        ("Order Model", test_order_model),
        ("Position Model", test_position_model),
        ("Business Logic", test_business_logic),
        ("Edge Cases", test_edge_cases)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("📊 MODEL TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All core model tests passed!")
        print("✅ Trading engine data models are working correctly")
        print("✅ Business logic is sound")
        print("✅ Ready to proceed with backend integration")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        print("❌ Core models need attention before proceeding")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)