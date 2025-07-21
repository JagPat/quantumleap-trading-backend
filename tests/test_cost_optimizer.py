"""
Test suite for Cost Optimizer
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.ai_engine.cost_optimizer import CostOptimizer, CostAlert

@pytest.fixture
def cost_optimizer():
    """Create a CostOptimizer instance for testing"""
    return CostOptimizer()

@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    with patch('app.ai_engine.cost_optimizer.get_db_connection') as mock:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_cursor

class TestCostOptimizer:
    """Test cases for CostOptimizer"""
    
    @pytest.mark.asyncio
    async def test_check_cost_limits_within_budget(self, cost_optimizer, mock_db_connection):
        """Test cost limit check when within budget"""
        # Mock user limits
        mock_db_connection.fetchone.return_value = ('{"openai": 1000}',)
        
        # Mock current usage
        with patch.object(cost_optimizer, 'get_daily_usage') as mock_usage:
            mock_usage.return_value = {"total_cost_cents": 500}
            
            result = await cost_optimizer.check_cost_limits("test_user", "openai", 200)
            
            assert result["within_limits"] is True
            assert result["current_cost_cents"] == 500
            assert result["estimated_cost_cents"] == 200
            assert result["projected_cost_cents"] == 700
            assert result["daily_limit_cents"] == 1000
            assert result["usage_percentage"] == 0.7
            assert result["remaining_budget_cents"] == 300
    
    @pytest.mark.asyncio
    async def test_check_cost_limits_exceeds_budget(self, cost_optimizer, mock_db_connection):
        """Test cost limit check when exceeding budget"""
        # Mock user limits
        mock_db_connection.fetchone.return_value = ('{"openai": 1000}',)
        
        # Mock current usage
        with patch.object(cost_optimizer, 'get_daily_usage') as mock_usage:
            mock_usage.return_value = {"total_cost_cents": 900}
            
            result = await cost_optimizer.check_cost_limits("test_user", "openai", 200)
            
            assert result["within_limits"] is False
            assert result["projected_cost_cents"] == 1100
            assert result["usage_percentage"] == 1.1
            assert result["alert_level"] == CostAlert.CRITICAL
    
    def test_get_alert_level(self, cost_optimizer):
        """Test alert level determination"""
        assert cost_optimizer.get_alert_level(0.3) == "normal"
        assert cost_optimizer.get_alert_level(0.6) == CostAlert.LOW
        assert cost_optimizer.get_alert_level(0.8) == CostAlert.MEDIUM
        assert cost_optimizer.get_alert_level(0.95) == CostAlert.HIGH
        assert cost_optimizer.get_alert_level(1.0) == CostAlert.CRITICAL
    
    @pytest.mark.asyncio
    async def test_get_user_cost_limits_with_data(self, cost_optimizer, mock_db_connection):
        """Test getting user cost limits when data exists"""
        mock_db_connection.fetchone.return_value = ('{"openai": 15, "claude": 20}',)
        
        result = await cost_optimizer.get_user_cost_limits("test_user")
        
        assert result["openai"] == 1500  # Converted to cents
        assert result["claude"] == 2000
    
    @pytest.mark.asyncio
    async def test_get_user_cost_limits_no_data(self, cost_optimizer, mock_db_connection):
        """Test getting user cost limits when no data exists"""
        mock_db_connection.fetchone.return_value = (None,)
        
        result = await cost_optimizer.get_user_cost_limits("test_user")
        
        # Should return default limits
        assert result["openai"] == cost_optimizer.default_daily_limit_cents
        assert result["claude"] == cost_optimizer.default_daily_limit_cents
    
    @pytest.mark.asyncio
    async def test_get_daily_usage(self, cost_optimizer, mock_db_connection):
        """Test getting daily usage statistics"""
        mock_db_connection.fetchone.return_value = (5, 1000, 500, 250.5)
        
        result = await cost_optimizer.get_daily_usage("test_user", "openai")
        
        assert result["requests"] == 5
        assert result["total_tokens"] == 1000
        assert result["total_cost_cents"] == 500
        assert result["avg_response_time_ms"] == 250.5
    
    @pytest.mark.asyncio
    async def test_suggest_cost_optimization(self, cost_optimizer):
        """Test cost optimization suggestions"""
        mock_usage_stats = {
            "provider_statistics": [
                {"provider": "openai", "requests": 10, "total_cost_cents": 1000, "success_rate": 95, "avg_response_time_ms": 200},
                {"provider": "claude", "requests": 8, "total_cost_cents": 600, "success_rate": 98, "avg_response_time_ms": 180}
            ],
            "operation_statistics": [
                {"operation_type": "analysis", "total_cost_cents": 800},
                {"operation_type": "chat", "total_cost_cents": 300}
            ],
            "total_cost_cents": 1100
        }
        
        with patch('app.ai_engine.cost_optimizer.get_ai_usage_stats') as mock_stats:
            mock_stats.return_value = mock_usage_stats
            
            result = await cost_optimizer.suggest_cost_optimization("test_user")
            
            assert result["user_id"] == "test_user"
            assert len(result["suggestions"]) > 0
            assert result["total_cost_cents"] == 1100
            
            # Should suggest using Claude (lower cost per request)
            provider_suggestion = next((s for s in result["suggestions"] if s["type"] == "provider_optimization"), None)
            assert provider_suggestion is not None
            assert "claude" in provider_suggestion["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_cost_trends(self, cost_optimizer, mock_db_connection):
        """Test getting cost trends"""
        mock_db_connection.fetchall.return_value = [
            ("2025-07-21", "openai", 500),
            ("2025-07-20", "openai", 300),
            ("2025-07-21", "claude", 200)
        ]
        
        result = await cost_optimizer.get_cost_trends("test_user", 7)
        
        assert len(result) == 3
        assert result[0]["date"] == "2025-07-21"
        assert result[0]["provider"] == "openai"
        assert result[0]["cost_cents"] == 500

class TestCostOptimizerIntegration:
    """Integration tests for CostOptimizer"""
    
    @pytest.mark.asyncio
    async def test_full_cost_check_workflow(self, cost_optimizer):
        """Test complete cost checking workflow"""
        with patch.object(cost_optimizer, 'get_user_cost_limits') as mock_limits, \
             patch.object(cost_optimizer, 'get_daily_usage') as mock_usage:
            
            mock_limits.return_value = {"openai": 1000}
            mock_usage.return_value = {"total_cost_cents": 800}
            
            # Test within limits
            result = await cost_optimizer.check_cost_limits("test_user", "openai", 100)
            assert result["within_limits"] is True
            assert result["alert_level"] == CostAlert.HIGH  # 90% usage
            
            # Test exceeding limits
            result = await cost_optimizer.check_cost_limits("test_user", "openai", 300)
            assert result["within_limits"] is False
            assert result["alert_level"] == CostAlert.CRITICAL
    
    @pytest.mark.asyncio
    async def test_cost_report_generation(self, cost_optimizer):
        """Test comprehensive cost report generation"""
        with patch('app.ai_engine.cost_optimizer.get_ai_usage_stats') as mock_stats, \
             patch.object(cost_optimizer, 'get_cost_trends') as mock_trends, \
             patch.object(cost_optimizer, 'suggest_cost_optimization') as mock_optimization:
            
            mock_stats.return_value = {
                "total_cost_cents": 1500,
                "total_requests": 50,
                "total_tokens": 10000,
                "provider_statistics": [],
                "operation_statistics": []
            }
            mock_trends.return_value = []
            mock_optimization.return_value = {"suggestions": []}
            
            result = await cost_optimizer.get_cost_report("test_user", 30)
            
            assert result["user_id"] == "test_user"
            assert result["report_period_days"] == 30
            assert result["summary"]["total_cost_cents"] == 1500
            assert result["summary"]["daily_average_cents"] == 50  # 1500/30
            assert result["summary"]["monthly_projection_cents"] == 1500  # 50*30

if __name__ == "__main__":
    pytest.main([__file__])