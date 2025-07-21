"""
Cost Optimizer
AI provider cost tracking and optimization system
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from ..database.service import get_db_connection, track_ai_usage, get_ai_usage_stats

logger = logging.getLogger(__name__)

class CostAlert(str, Enum):
    """Cost alert levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CostOptimizer:
    """
    Cost optimization system for AI provider usage
    """
    
    def __init__(self):
        self.default_daily_limit_cents = 1000  # $10 default daily limit
        self.alert_thresholds = {
            CostAlert.LOW: 0.5,      # 50% of limit
            CostAlert.MEDIUM: 0.75,  # 75% of limit
            CostAlert.HIGH: 0.9,     # 90% of limit
            CostAlert.CRITICAL: 1.0  # 100% of limit
        }
    
    async def check_cost_limits(self, user_id: str, provider: str, estimated_cost_cents: int) -> Dict[str, Any]:
        """Check if operation would exceed cost limits"""
        
        try:
            # Get user's cost limits
            user_limits = await self.get_user_cost_limits(user_id)
            daily_limit = user_limits.get(provider, self.default_daily_limit_cents)
            
            # Get current usage for today
            current_usage = await self.get_daily_usage(user_id, provider)
            current_cost = current_usage.get("total_cost_cents", 0)
            
            # Calculate projected cost
            projected_cost = current_cost + estimated_cost_cents
            
            # Check if within limits
            within_limits = projected_cost <= daily_limit
            usage_percentage = projected_cost / daily_limit if daily_limit > 0 else 0
            
            # Determine alert level
            alert_level = self.get_alert_level(usage_percentage)
            
            return {
                "within_limits": within_limits,
                "current_cost_cents": current_cost,
                "estimated_cost_cents": estimated_cost_cents,
                "projected_cost_cents": projected_cost,
                "daily_limit_cents": daily_limit,
                "usage_percentage": usage_percentage,
                "alert_level": alert_level,
                "remaining_budget_cents": max(0, daily_limit - projected_cost)
            }
            
        except Exception as e:
            logger.error(f"Failed to check cost limits for user {user_id}: {e}")
            return {
                "within_limits": True,  # Default to allowing operation
                "error": str(e)
            }
    
    def get_alert_level(self, usage_percentage: float) -> str:
        """Determine alert level based on usage percentage"""
        
        if usage_percentage >= self.alert_thresholds[CostAlert.CRITICAL]:
            return CostAlert.CRITICAL
        elif usage_percentage >= self.alert_thresholds[CostAlert.HIGH]:
            return CostAlert.HIGH
        elif usage_percentage >= self.alert_thresholds[CostAlert.MEDIUM]:
            return CostAlert.MEDIUM
        elif usage_percentage >= self.alert_thresholds[CostAlert.LOW]:
            return CostAlert.LOW
        else:
            return "normal"
    
    async def get_user_cost_limits(self, user_id: str) -> Dict[str, int]:
        """Get user's cost limits per provider"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cost_limits FROM ai_user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                cost_limits = json.loads(result[0])
                # Convert to cents if stored in dollars
                return {
                    provider: int(limit * 100) if limit < 100 else int(limit)
                    for provider, limit in cost_limits.items()
                }
            
            # Return default limits
            return {
                "openai": self.default_daily_limit_cents,
                "claude": self.default_daily_limit_cents,
                "gemini": self.default_daily_limit_cents,
                "grok": self.default_daily_limit_cents
            }
            
        except Exception as e:
            logger.error(f"Failed to get cost limits for user {user_id}: {e}")
            return {}
    
    async def get_daily_usage(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Get today's usage for a specific provider"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            today = datetime.now().date()
            cursor.execute("""
                SELECT 
                    COUNT(*) as requests,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost_cents) as total_cost_cents,
                    AVG(response_time_ms) as avg_response_time
                FROM ai_usage_tracking
                WHERE user_id = ? AND provider = ? 
                AND DATE(created_at) = ?
            """, (user_id, provider, today))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "requests": result[0] or 0,
                    "total_tokens": result[1] or 0,
                    "total_cost_cents": result[2] or 0,
                    "avg_response_time_ms": result[3] or 0
                }
            
            return {
                "requests": 0,
                "total_tokens": 0,
                "total_cost_cents": 0,
                "avg_response_time_ms": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get daily usage for user {user_id}, provider {provider}: {e}")
            return {"requests": 0, "total_tokens": 0, "total_cost_cents": 0}
    
    async def suggest_cost_optimization(self, user_id: str) -> Dict[str, Any]:
        """Suggest cost optimization strategies"""
        
        try:
            # Get usage statistics for the last 7 days
            usage_stats = get_ai_usage_stats(user_id, days=7)
            
            suggestions = []
            
            # Analyze provider costs
            provider_stats = usage_stats.get("provider_statistics", [])
            if len(provider_stats) > 1:
                # Sort by cost efficiency (cost per request)
                efficiency_data = []
                for provider in provider_stats:
                    if provider["requests"] > 0:
                        cost_per_request = provider["total_cost_cents"] / provider["requests"]
                        efficiency_data.append({
                            "provider": provider["provider"],
                            "cost_per_request": cost_per_request,
                            "success_rate": provider["success_rate"],
                            "avg_response_time": provider["avg_response_time_ms"]
                        })
                
                if efficiency_data:
                    # Find most cost-effective provider
                    most_efficient = min(efficiency_data, key=lambda x: x["cost_per_request"])
                    suggestions.append({
                        "type": "provider_optimization",
                        "message": f"Consider using {most_efficient['provider']} more often - it has the lowest cost per request",
                        "data": most_efficient
                    })
            
            # Check for high-cost operations
            operation_stats = usage_stats.get("operation_statistics", [])
            high_cost_ops = [op for op in operation_stats if op["total_cost_cents"] > 500]  # $5+
            
            if high_cost_ops:
                suggestions.append({
                    "type": "operation_optimization",
                    "message": "Consider optimizing high-cost operations",
                    "data": high_cost_ops
                })
            
            # Check usage patterns
            total_cost = usage_stats.get("total_cost_cents", 0)
            if total_cost > 700:  # $7+ per week
                suggestions.append({
                    "type": "budget_alert",
                    "message": "Weekly spending is high. Consider setting stricter daily limits",
                    "data": {"weekly_cost_cents": total_cost}
                })
            
            return {
                "user_id": user_id,
                "analysis_period_days": 7,
                "total_cost_cents": total_cost,
                "suggestions": suggestions,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cost optimization suggestions for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "suggestions": [],
                "error": str(e)
            }
    
    async def set_cost_alert(self, user_id: str, provider: str, threshold_percentage: float) -> bool:
        """Set cost alert threshold for a provider"""
        
        try:
            # Store alert configuration
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if alert config exists
            cursor.execute("""
                SELECT id FROM ai_cost_alerts 
                WHERE user_id = ? AND provider = ?
            """, (user_id, provider))
            
            if cursor.fetchone():
                # Update existing alert
                cursor.execute("""
                    UPDATE ai_cost_alerts 
                    SET threshold_percentage = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND provider = ?
                """, (threshold_percentage, user_id, provider))
            else:
                # Create new alert
                cursor.execute("""
                    INSERT INTO ai_cost_alerts 
                    (user_id, provider, threshold_percentage, is_active)
                    VALUES (?, ?, ?, TRUE)
                """, (user_id, provider, threshold_percentage))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Set cost alert for user {user_id}, provider {provider} at {threshold_percentage}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cost alert: {e}")
            return False
    
    async def check_and_send_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Check current usage and send alerts if thresholds are exceeded"""
        
        alerts_sent = []
        
        try:
            # Get user's providers and limits
            user_limits = await self.get_user_cost_limits(user_id)
            
            for provider, daily_limit in user_limits.items():
                # Get current usage
                current_usage = await self.get_daily_usage(user_id, provider)
                current_cost = current_usage.get("total_cost_cents", 0)
                
                if daily_limit > 0:
                    usage_percentage = current_cost / daily_limit
                    alert_level = self.get_alert_level(usage_percentage)
                    
                    if alert_level != "normal":
                        alert_data = {
                            "user_id": user_id,
                            "provider": provider,
                            "alert_level": alert_level,
                            "current_cost_cents": current_cost,
                            "daily_limit_cents": daily_limit,
                            "usage_percentage": usage_percentage,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Send alert (in production, this would send email/notification)
                        logger.warning(f"Cost alert for user {user_id}: {alert_level} usage on {provider}")
                        alerts_sent.append(alert_data)
            
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Failed to check and send alerts for user {user_id}: {e}")
            return []
    
    async def get_cost_report(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive cost report"""
        
        try:
            # Get usage statistics
            usage_stats = get_ai_usage_stats(user_id, days=days)
            
            # Get cost trends (daily breakdown)
            cost_trends = await self.get_cost_trends(user_id, days)
            
            # Get optimization suggestions
            optimization = await self.suggest_cost_optimization(user_id)
            
            # Calculate projections
            daily_average = usage_stats.get("total_cost_cents", 0) / days if days > 0 else 0
            monthly_projection = daily_average * 30
            
            return {
                "user_id": user_id,
                "report_period_days": days,
                "summary": {
                    "total_cost_cents": usage_stats.get("total_cost_cents", 0),
                    "total_requests": usage_stats.get("total_requests", 0),
                    "total_tokens": usage_stats.get("total_tokens", 0),
                    "daily_average_cents": daily_average,
                    "monthly_projection_cents": monthly_projection
                },
                "provider_breakdown": usage_stats.get("provider_statistics", []),
                "operation_breakdown": usage_stats.get("operation_statistics", []),
                "cost_trends": cost_trends,
                "optimization_suggestions": optimization.get("suggestions", []),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cost report for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }
    
    async def get_cost_trends(self, user_id: str, days: int) -> List[Dict[str, Any]]:
        """Get daily cost trends"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    provider,
                    SUM(cost_cents) as daily_cost
                FROM ai_usage_tracking
                WHERE user_id = ? 
                AND created_at >= datetime('now', ? || ' days')
                GROUP BY DATE(created_at), provider
                ORDER BY date DESC
            """, (user_id, f"-{days}"))
            
            results = cursor.fetchall()
            conn.close()
            
            trends = []
            for result in results:
                trends.append({
                    "date": result[0],
                    "provider": result[1],
                    "cost_cents": result[2]
                })
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get cost trends for user {user_id}: {e}")
            return []