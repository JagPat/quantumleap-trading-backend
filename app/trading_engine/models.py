"""
Trading Engine Models
Data models for orders, positions, executions, and related entities
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

class OrderType(str, Enum):
    """Order types supported by the trading engine"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(str, Enum):
    """Order side (buy or sell)"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    """Order status throughout its lifecycle"""
    PENDING = "PENDING"          # Created but not yet submitted
    SUBMITTED = "SUBMITTED"      # Submitted to broker
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partially executed
    FILLED = "FILLED"           # Completely executed
    CANCELLED = "CANCELLED"     # Cancelled by user or system
    REJECTED = "REJECTED"       # Rejected by broker
    EXPIRED = "EXPIRED"         # Expired (for GTD orders)

class PositionStatus(str, Enum):
    """Position status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class StrategyStatus(str, Enum):
    """Strategy deployment status"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

@dataclass
class Order:
    """Order data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    symbol: str = ""
    order_type: OrderType = OrderType.MARKET
    side: OrderSide = OrderSide.BUY
    quantity: int = 0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None
    strategy_id: Optional[str] = None
    signal_id: Optional[str] = None
    filled_quantity: int = 0
    average_fill_price: Optional[float] = None
    commission: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "broker_order_id": self.broker_order_id,
            "strategy_id": self.strategy_id,
            "signal_id": self.signal_id,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "commission": self.commission,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create order from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            symbol=data.get("symbol", ""),
            order_type=OrderType(data.get("order_type", "MARKET")),
            side=OrderSide(data.get("side", "BUY")),
            quantity=data.get("quantity", 0),
            price=data.get("price"),
            stop_price=data.get("stop_price"),
            status=OrderStatus(data.get("status", "PENDING")),
            broker_order_id=data.get("broker_order_id"),
            strategy_id=data.get("strategy_id"),
            signal_id=data.get("signal_id"),
            filled_quantity=data.get("filled_quantity", 0),
            average_fill_price=data.get("average_fill_price"),
            commission=data.get("commission", 0.0),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            submitted_at=datetime.fromisoformat(data["submitted_at"]) if data.get("submitted_at") else None,
            filled_at=datetime.fromisoformat(data["filled_at"]) if data.get("filled_at") else None
        )
    
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        """Check if order is active (can still be filled)"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    def remaining_quantity(self) -> int:
        """Get remaining quantity to be filled"""
        return self.quantity - self.filled_quantity

@dataclass
class OrderResult:
    """Result of order processing operations"""
    success: bool
    order: Optional['Order'] = None
    error_message: Optional[str] = None
    broker_order_id: Optional[str] = None
    execution_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "order": self.order.to_dict() if self.order else None,
            "error_message": self.error_message,
            "broker_order_id": self.broker_order_id,
            "execution_details": self.execution_details
        }

@dataclass
class Position:
    """Position data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    symbol: str = ""
    quantity: int = 0
    average_price: float = 0.0
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    strategy_id: Optional[str] = None
    status: PositionStatus = PositionStatus.OPEN
    opened_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "strategy_id": self.strategy_id,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create position from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            symbol=data.get("symbol", ""),
            quantity=data.get("quantity", 0),
            average_price=data.get("average_price", 0.0),
            current_price=data.get("current_price"),
            unrealized_pnl=data.get("unrealized_pnl", 0.0),
            realized_pnl=data.get("realized_pnl", 0.0),
            strategy_id=data.get("strategy_id"),
            status=PositionStatus(data.get("status", "OPEN")),
            opened_at=datetime.fromisoformat(data["opened_at"]) if data.get("opened_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            closed_at=datetime.fromisoformat(data["closed_at"]) if data.get("closed_at") else None
        )
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L based on current price"""
        if self.quantity == 0:
            return 0.0
        
        price_diff = current_price - self.average_price
        if self.quantity > 0:  # Long position
            return price_diff * self.quantity
        else:  # Short position
            return -price_diff * abs(self.quantity)
    
    def update_current_price(self, current_price: float):
        """Update current price and recalculate unrealized P&L"""
        self.current_price = current_price
        self.unrealized_pnl = self.calculate_unrealized_pnl(current_price)
        self.updated_at = datetime.now()

@dataclass
class Execution:
    """Trade execution data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    user_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: int = 0
    price: float = 0.0
    commission: float = 0.0
    broker_execution_id: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "broker_execution_id": self.broker_execution_id,
            "executed_at": self.executed_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Execution':
        """Create execution from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            order_id=data.get("order_id", ""),
            user_id=data.get("user_id", ""),
            symbol=data.get("symbol", ""),
            side=OrderSide(data.get("side", "BUY")),
            quantity=data.get("quantity", 0),
            price=data.get("price", 0.0),
            commission=data.get("commission", 0.0),
            broker_execution_id=data.get("broker_execution_id"),
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else datetime.now()
        )

@dataclass
class StrategyDeployment:
    """Strategy deployment data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    strategy_id: str = ""
    status: StrategyStatus = StrategyStatus.ACTIVE
    configuration: Dict[str, Any] = field(default_factory=dict)
    risk_parameters: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    deployed_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    paused_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert deployment to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "strategy_id": self.strategy_id,
            "status": self.status.value,
            "configuration": self.configuration,
            "risk_parameters": self.risk_parameters,
            "performance_metrics": self.performance_metrics,
            "deployed_at": self.deployed_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyDeployment':
        """Create deployment from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            strategy_id=data.get("strategy_id", ""),
            status=StrategyStatus(data.get("status", "ACTIVE")),
            configuration=data.get("configuration", {}),
            risk_parameters=data.get("risk_parameters", {}),
            performance_metrics=data.get("performance_metrics", {}),
            deployed_at=datetime.fromisoformat(data["deployed_at"]) if data.get("deployed_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            paused_at=datetime.fromisoformat(data["paused_at"]) if data.get("paused_at") else None,
            stopped_at=datetime.fromisoformat(data["stopped_at"]) if data.get("stopped_at") else None,
            error_message=data.get("error_message")
        )

@dataclass
class TradingSignal:
    """Trading signal data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    symbol: str = ""
    signal_type: str = "BUY"  # BUY, SELL, HOLD
    confidence_score: float = 0.0
    reasoning: str = ""
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: float = 0.02  # Default 2% position size
    strategy_id: Optional[str] = None
    provider_used: Optional[str] = None
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "strategy_id": self.strategy_id,
            "provider_used": self.provider_used,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """Create signal from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            symbol=data.get("symbol", ""),
            signal_type=data.get("signal_type", "BUY"),
            confidence_score=data.get("confidence_score", 0.0),
            reasoning=data.get("reasoning", ""),
            target_price=data.get("target_price"),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            position_size=data.get("position_size", 0.02),
            strategy_id=data.get("strategy_id"),
            provider_used=data.get("provider_used"),
            is_active=data.get("is_active", True),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )
    
    def is_expired(self) -> bool:
        """Check if signal has expired"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

# Market Data Models

class MarketState(str, Enum):
    """Market state enumeration"""
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    OPEN = "open"
    POST_MARKET = "post_market"
    HOLIDAY = "holiday"

@dataclass
class MarketStatus:
    """Market status information"""
    state: MarketState
    is_open: bool
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None
    timezone: str = "UTC"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "state": self.state.value,
            "is_open": self.is_open,
            "next_open": self.next_open.isoformat() if self.next_open else None,
            "next_close": self.next_close.isoformat() if self.next_close else None,
            "timezone": self.timezone
        }

@dataclass
class PriceData:
    """Real-time price data"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime
    change: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "change": self.change,
            "change_percent": self.change_percent,
            "high": self.high,
            "low": self.low,
            "open": self.open_price
        }

@dataclass
class MarketHours:
    """Market hours information"""
    open_time: datetime
    close_time: datetime
    timezone: str = "UTC"
    is_trading_day: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "open_time": self.open_time.isoformat(),
            "close_time": self.close_time.isoformat(),
            "timezone": self.timezone,
            "is_trading_day": self.is_trading_day
        }

# Signal and Event Models

class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class SignalPriority(str, Enum):
    """Signal priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class Signal:
    """Enhanced trading signal model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    symbol: str = ""
    signal_type: SignalType = SignalType.BUY
    confidence_score: float = 0.0
    priority: SignalPriority = SignalPriority.MEDIUM
    reasoning: str = ""
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: float = 2.0  # Percentage of portfolio
    strategy_id: Optional[str] = None
    provider_used: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "confidence_score": self.confidence_score,
            "priority": self.priority.value,
            "reasoning": self.reasoning,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size_pct": self.position_size_pct,
            "strategy_id": self.strategy_id,
            "provider_used": self.provider_used,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat()
        }