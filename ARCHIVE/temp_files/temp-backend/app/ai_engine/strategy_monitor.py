"""
Strategy Monitor
Strategy execution monitoring and performance tracking
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class StrategyStatus(str, Enum):
    """Strategy execution status"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class TradeStatus(str, Enum):
    """Individual trade status"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class StrategyMonitor:
    """
    Monitors strategy execution and tracks performance
    """
    
    def __init__(self):
        pass
    
    async def deploy_strategy(
        self, 
        user_id: str, 
        strategy_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy a strategy for live execution"""
        
        try:
            strategy_id = strategy_config.get("id")
            
            # Validate strategy configuration
            validation_result = await self.validate_strategy_config(strategy_config)
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "message": f"Strategy validation failed: {validation_result['error']}"
                }
            
            # Create deployment record
            deployment = {
                "strategy_id": strategy_id,
                "user_id": user_id,
                "status": StrategyStatus.ACTIVE,
                "deployed_at": datetime.now().isoformat(),
                "configuration": strategy_config,
                "performance": {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_pnl": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0
                }
            }
            
            # Store deployment (in production, this would go to database)
            await self.store_strategy_deployment(deployment)
            
            logger.info(f"Strategy {strategy_id} deployed for user {user_id}")
            
            return {
                "status": "success",
                "deployment": deployment,
                "message": "Strategy deployed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy strategy: {e}")
            return {
                "status": "error",
                "message": f"Deployment failed: {str(e)}"
            }
    
    async def validate_strategy_config(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy configuration before deployment"""
        
        try:
            required_fields = ["id", "name", "type", "configuration"]
            missing_fields = []
            
            for field in required_fields:
                if field not in strategy_config:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Missing required fields: {missing_fields}"
                }
            
            # Validate risk management parameters
            config = strategy_config.get("configuration", {})
            risk_mgmt = config.get("risk_management", {})
            
            if not risk_mgmt:
                return {
                    "valid": False,
                    "error": "Risk management configuration is required"
                }
            
            # Check required risk parameters
            required_risk_params = ["max_position_size", "stop_loss_percentage"]
            for param in required_risk_params:
                if param not in risk_mgmt:
                    return {
                        "valid": False,
                        "error": f"Missing risk parameter: {param}"
                    }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    async def get_strategy_performance(
        self, 
        user_id: str, 
        strategy_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        
        try:
            # In production, this would query actual trade data
            # For now, generate mock performance data
            
            mock_performance = {
                "strategy_id": strategy_id,
                "period_days": period_days,
                "summary": {
                    "total_trades": 15,
                    "winning_trades": 9,
                    "losing_trades": 6,
                    "win_rate": 60.0,
                    "total_pnl": 12500.0,
                    "total_return_pct": 8.5,
                    "max_drawdown": 3.2,
                    "sharpe_ratio": 1.4,
                    "avg_trade_duration": "2.3 days"
                },
                "daily_returns": self.generate_mock_daily_returns(period_days),
                "trade_history": self.generate_mock_trade_history(15),
                "risk_metrics": {
                    "var_95": 2.1,  # Value at Risk 95%
                    "max_consecutive_losses": 3,
                    "largest_loss": -850.0,
                    "largest_win": 1200.0
                },
                "last_updated": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "performance": mock_performance
            }
            
        except Exception as e:
            logger.error(f"Failed to get strategy performance: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve performance: {str(e)}"
            }
    
    def generate_mock_daily_returns(self, days: int) -> List[Dict[str, Any]]:
        """Generate mock daily returns for performance visualization"""
        
        import random
        
        daily_returns = []
        cumulative_return = 0.0
        
        for i in range(days):
            # Generate random daily return between -2% and +3%
            daily_return = random.uniform(-0.02, 0.03)
            cumulative_return += daily_return
            
            daily_returns.append({
                "date": (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d"),
                "daily_return": round(daily_return * 100, 2),
                "cumulative_return": round(cumulative_return * 100, 2)
            })
        
        return daily_returns
    
    def generate_mock_trade_history(self, trade_count: int) -> List[Dict[str, Any]]:
        """Generate mock trade history"""
        
        import random
        
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC", "WIPRO", "MARUTI"]
        trade_history = []
        
        for i in range(trade_count):
            symbol = random.choice(symbols)
            entry_price = random.uniform(100, 3000)
            exit_price = entry_price * random.uniform(0.95, 1.08)  # -5% to +8%
            quantity = random.randint(10, 100)
            
            pnl = (exit_price - entry_price) * quantity
            
            trade = {
                "trade_id": f"trade_{i+1}",
                "symbol": symbol,
                "entry_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                "exit_date": (datetime.now() - timedelta(days=random.randint(0, 25))).strftime("%Y-%m-%d"),
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "quantity": quantity,
                "pnl": round(pnl, 2),
                "return_pct": round(((exit_price - entry_price) / entry_price) * 100, 2),
                "status": TradeStatus.CLOSED
            }
            
            trade_history.append(trade)
        
        return sorted(trade_history, key=lambda x: x["exit_date"], reverse=True)
    
    async def monitor_active_strategies(self, user_id: str) -> Dict[str, Any]:
        """Monitor all active strategies for a user"""
        
        try:
            # In production, this would query database for active strategies
            active_strategies = [
                {
                    "strategy_id": f"strategy_{user_id}_1",
                    "name": "Momentum Strategy",
                    "status": StrategyStatus.ACTIVE,
                    "deployed_at": "2025-01-20T10:00:00Z",
                    "current_positions": 2,
                    "daily_pnl": 450.0,
                    "alerts": []
                },
                {
                    "strategy_id": f"strategy_{user_id}_2",
                    "name": "Mean Reversion",
                    "status": StrategyStatus.ACTIVE,
                    "deployed_at": "2025-01-19T15:30:00Z",
                    "current_positions": 1,
                    "daily_pnl": -120.0,
                    "alerts": ["Position approaching stop loss"]
                }
            ]
            
            return {
                "status": "success",
                "active_strategies": active_strategies,
                "total_active": len(active_strategies),
                "monitoring_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to monitor strategies: {e}")
            return {
                "status": "error",
                "message": f"Monitoring failed: {str(e)}"
            }
    
    async def pause_strategy(self, user_id: str, strategy_id: str) -> Dict[str, Any]:
        """Pause strategy execution"""
        
        try:
            # In production, this would update database and stop execution
            
            return {
                "status": "success",
                "strategy_id": strategy_id,
                "new_status": StrategyStatus.PAUSED,
                "paused_at": datetime.now().isoformat(),
                "message": "Strategy paused successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to pause strategy {strategy_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to pause strategy: {str(e)}"
            }
    
    async def resume_strategy(self, user_id: str, strategy_id: str) -> Dict[str, Any]:
        """Resume paused strategy execution"""
        
        try:
            # In production, this would update database and restart execution
            
            return {
                "status": "success",
                "strategy_id": strategy_id,
                "new_status": StrategyStatus.ACTIVE,
                "resumed_at": datetime.now().isoformat(),
                "message": "Strategy resumed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to resume strategy {strategy_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to resume strategy: {str(e)}"
            }
    
    async def stop_strategy(self, user_id: str, strategy_id: str) -> Dict[str, Any]:
        """Stop strategy execution permanently"""
        
        try:
            # In production, this would close all positions and stop execution
            
            return {
                "status": "success",
                "strategy_id": strategy_id,
                "new_status": StrategyStatus.STOPPED,
                "stopped_at": datetime.now().isoformat(),
                "message": "Strategy stopped successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to stop strategy: {str(e)}"
            }
    
    async def get_strategy_alerts(self, user_id: str, strategy_id: str) -> Dict[str, Any]:
        """Get alerts and notifications for a strategy"""
        
        try:
            # Mock alerts - in production, these would be real-time alerts
            mock_alerts = [
                {
                    "alert_id": "alert_1",
                    "type": "risk_warning",
                    "message": "Position size approaching maximum limit",
                    "severity": "medium",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "alert_id": "alert_2",
                    "type": "performance",
                    "message": "Strategy outperforming benchmark by 3%",
                    "severity": "info",
                    "created_at": (datetime.now() - timedelta(hours=2)).isoformat()
                }
            ]
            
            return {
                "status": "success",
                "alerts": mock_alerts,
                "strategy_id": strategy_id,
                "alert_count": len(mock_alerts)
            }
            
        except Exception as e:
            logger.error(f"Failed to get strategy alerts: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve alerts: {str(e)}"
            }
    
    async def store_strategy_deployment(self, deployment: Dict[str, Any]):
        """Store strategy deployment record"""
        
        try:
            # In production, this would store in database
            # For now, just log the deployment
            logger.info(f"Strategy deployment stored: {deployment['strategy_id']}")
            
        except Exception as e:
            logger.error(f"Failed to store strategy deployment: {e}")
    
    async def update_strategy_performance(
        self, 
        strategy_id: str, 
        trade_result: Dict[str, Any]
    ):
        """Update strategy performance with new trade result"""
        
        try:
            # In production, this would update performance metrics in database
            logger.info(f"Performance updated for strategy {strategy_id}: {trade_result}")
            
        except Exception as e:
            logger.error(f"Failed to update strategy performance: {e}")