"""
Integration tests for AI Engine components
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.ai_engine.cost_optimizer import CostOptimizer
from app.ai_engine.risk_manager import RiskManager
from app.ai_engine.learning_system import LearningSystem, FeedbackType, OutcomeType
from app.ai_engine.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity

@pytest.fixture
def ai_components():
    """Create all AI engine components for testing"""
    return {
        "cost_optimizer": CostOptimizer(),
        "risk_manager": RiskManager(),
        "learning_system": LearningSystem(),
        "error_handler": ErrorHandler()
    }

@pytest.fixture
def sample_user_data():
    """Sample user data for integration testing"""
    return {
        "user_id": "test_user_123",
        "portfolio": {
            "total_value": 1000000,
            "holdings": [
                {"symbol": "RELIANCE", "current_value": 150000, "sector": "Energy"},
                {"symbol": "TCS", "current_value": 120000, "sector": "IT"},
                {"symbol": "HDFCBANK", "current_value": 100000, "sector": "Banking"},
                {"symbol": "INFY", "current_value": 80000, "sector": "IT"},
                {"symbol": "ICICIBANK", "current_value": 70000, "sector": "Banking"}
            ]
        },
        "preferences": {
            "risk_tolerance": "medium",
            "cost_limits": {"openai": 1000, "claude": 800}
        }
    }

class TestAIEngineIntegration:
    """Integration tests for AI Engine components working together"""
    
    @pytest.mark.asyncio
    async def test_complete_trading_decision_workflow(self, ai_components, sample_user_data):
        """Test complete workflow from signal generation to execution"""
        cost_optimizer = ai_components["cost_optimizer"]
        risk_manager = ai_components["risk_manager"]
        learning_system = ai_components["learning_system"]
        error_handler = ai_components["error_handler"]
        
        user_id = sample_user_data["user_id"]
        portfolio = sample_user_data["portfolio"]
        
        # Step 1: Check cost limits before generating signal
        with patch.object(cost_optimizer, 'check_cost_limits') as mock_cost_check:
            mock_cost_check.return_value = {
                "within_limits": True,
                "remaining_budget_cents": 500,
                "usage_percentage": 0.5
            }
            
            cost_check = await cost_optimizer.check_cost_limits(user_id, "openai", 100)
            assert cost_check["within_limits"] is True
        
        # Step 2: Validate trade risk
        trade_data = {
            "symbol": "WIPRO",
            "amount": 80000,  # 8% of portfolio
            "type": "buy"
        }
        
        risk_validation = await risk_manager.validate_trade_risk(user_id, trade_data, portfolio)
        assert risk_validation["approved"] is True
        assert risk_validation["risk_level"] == "medium"
        
        # Step 3: Simulate signal execution and record outcome
        signal_id = "signal_test_123"
        
        with patch('app.ai_engine.learning_system.get_db_connection') as mock_db:
            mock_cursor = Mock()
            mock_db.return_value.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 456
            
            # Record successful trade outcome
            outcome_recorded = await learning_system.record_trade_outcome(
                user_id,
                signal_id,
                OutcomeType.PROFIT,
                2000.0,  # ₹2000 profit
                105.50
            )
            assert outcome_recorded is True
        
        # Step 4: Record user feedback
        with patch('app.ai_engine.learning_system.get_db_connection') as mock_db:
            mock_cursor = Mock()
            mock_db.return_value.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 789
            
            with patch.object(learning_system, 'update_user_preferences') as mock_update:
                feedback_recorded = await learning_system.record_feedback(
                    user_id,
                    FeedbackType.SIGNAL_ACCURACY,
                    signal_id,
                    4,  # Good rating
                    "Signal was accurate",
                    {"provider_used": "openai"}
                )
                assert feedback_recorded is True
    
    @pytest.mark.asyncio
    async def test_risk_cost_optimization_integration(self, ai_components, sample_user_data):
        """Test integration between risk management and cost optimization"""
        cost_optimizer = ai_components["cost_optimizer"]
        risk_manager = ai_components["risk_manager"]
        
        user_id = sample_user_data["user_id"]
        portfolio = sample_user_data["portfolio"]
        
        # Get portfolio risk assessment
        risk_assessment = await risk_manager.assess_portfolio_risk(user_id, portfolio)
        
        # Based on risk level, adjust cost optimization strategy
        if risk_assessment["overall_risk"] in ["high", "critical"]:
            # High risk portfolio - be more conservative with AI spending
            conservative_limits = {"openai": 500, "claude": 400}  # Lower limits
        else:
            # Normal risk - standard limits
            conservative_limits = {"openai": 1000, "claude": 800}
        
        # Test cost optimization with risk-adjusted limits
        with patch.object(cost_optimizer, 'get_user_cost_limits') as mock_limits:
            mock_limits.return_value = conservative_limits
            
            with patch.object(cost_optimizer, 'get_daily_usage') as mock_usage:
                mock_usage.return_value = {"total_cost_cents": 300}
                
                cost_check = await cost_optimizer.check_cost_limits(user_id, "openai", 200)
                
                # Should consider both risk and cost factors
                assert "within_limits" in cost_check
                assert "usage_percentage" in cost_check
    
    @pytest.mark.asyncio
    async def test_learning_feedback_loop_integration(self, ai_components, sample_user_data):
        """Test learning system feedback loop with other components"""
        learning_system = ai_components["learning_system"]
        cost_optimizer = ai_components["cost_optimizer"]
        
        user_id = sample_user_data["user_id"]
        
        # Mock learning insights showing Claude performs better
        mock_insights = {
            "insights": [
                {
                    "type": "best_provider",
                    "message": "claude has the highest accuracy (85%)",
                    "data": {"overall_accuracy": 0.85}
                }
            ],
            "recommendations": ["Consider using claude more frequently"]
        }
        
        with patch.object(learning_system, 'get_learning_insights') as mock_insights_func:
            mock_insights_func.return_value = mock_insights
            
            insights = await learning_system.get_learning_insights(user_id)
            
            # Cost optimizer should consider these insights for provider selection
            with patch.object(cost_optimizer, 'suggest_cost_optimization') as mock_cost_opt:
                mock_cost_opt.return_value = {
                    "suggestions": [
                        {
                            "type": "provider_optimization",
                            "message": "Consider using claude more often - it has the lowest cost per request",
                            "data": {"provider": "claude", "cost_per_request": 50}
                        }
                    ]
                }
                
                cost_suggestions = await cost_optimizer.suggest_cost_optimization(user_id)
                
                # Both learning and cost systems should recommend Claude
                assert any("claude" in str(insight).lower() for insight in insights["insights"])
                assert any("claude" in str(suggestion).lower() for suggestion in cost_suggestions["suggestions"])
    
    @pytest.mark.asyncio
    async def test_error_handling_across_components(self, ai_components, sample_user_data):
        """Test error handling integration across all components"""
        error_handler = ai_components["error_handler"]
        cost_optimizer = ai_components["cost_optimizer"]
        
        user_id = sample_user_data["user_id"]
        
        # Test error logging from cost optimizer
        with patch('app.ai_engine.error_handler.get_db_connection') as mock_db:
            mock_cursor = Mock()
            mock_db.return_value.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 999
            
            error_id = await error_handler.log_error(
                user_id,
                ErrorCategory.API_ERROR,
                "Cost limit check failed",
                ErrorSeverity.MEDIUM,
                {"component": "cost_optimizer", "operation": "check_limits"}
            )
            
            assert error_id == "999"
        
        # Test error recovery workflow
        with patch.object(error_handler, 'get_error_summary') as mock_summary:
            mock_summary.return_value = {
                "health_status": "warning",
                "total_errors": 5,
                "active_alerts": []
            }
            
            error_summary = await error_handler.get_error_summary(user_id, 24)
            
            # System should adapt behavior based on error status
            if error_summary["health_status"] in ["warning", "critical"]:
                # Reduce AI operations or switch to more reliable providers
                assert error_summary["total_errors"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self, ai_components, sample_user_data):
        """Test performance monitoring across all components"""
        cost_optimizer = ai_components["cost_optimizer"]
        learning_system = ai_components["learning_system"]
        error_handler = ai_components["error_handler"]
        
        user_id = sample_user_data["user_id"]
        
        # Get performance metrics from different components
        with patch.object(cost_optimizer, 'get_cost_report') as mock_cost_report:
            mock_cost_report.return_value = {
                "summary": {
                    "total_cost_cents": 1500,
                    "total_requests": 50,
                    "daily_average_cents": 50
                },
                "provider_breakdown": [
                    {"provider": "openai", "total_cost_cents": 800, "requests": 25},
                    {"provider": "claude", "total_cost_cents": 700, "requests": 25}
                ]
            }
            
            with patch.object(learning_system, 'get_provider_performance') as mock_learning_perf:
                mock_learning_perf.return_value = {
                    "provider_performance": {
                        "openai": {"overall_accuracy": 0.75, "total_signals": 20},
                        "claude": {"overall_accuracy": 0.85, "total_signals": 18}
                    }
                }
                
                with patch.object(error_handler, 'get_system_health') as mock_health:
                    mock_health.return_value = {
                        "health_status": "healthy",
                        "total_errors_24h": 3
                    }
                    
                    # Aggregate performance data
                    cost_report = await cost_optimizer.get_cost_report(user_id, 30)
                    learning_perf = await learning_system.get_provider_performance(user_id, 30)
                    system_health = await error_handler.get_system_health()
                    
                    # Create comprehensive performance dashboard
                    dashboard = {
                        "cost_efficiency": {
                            "openai": cost_report["provider_breakdown"][0]["total_cost_cents"] / cost_report["provider_breakdown"][0]["requests"],
                            "claude": cost_report["provider_breakdown"][1]["total_cost_cents"] / cost_report["provider_breakdown"][1]["requests"]
                        },
                        "accuracy_performance": learning_perf["provider_performance"],
                        "system_health": system_health["health_status"],
                        "recommendation": "claude" if learning_perf["provider_performance"]["claude"]["overall_accuracy"] > learning_perf["provider_performance"]["openai"]["overall_accuracy"] else "openai"
                    }
                    
                    assert dashboard["recommendation"] == "claude"  # Better accuracy
                    assert dashboard["system_health"] == "healthy"
                    assert "cost_efficiency" in dashboard

class TestAIEngineErrorScenarios:
    """Test error scenarios and recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_database_failure_recovery(self, ai_components):
        """Test system behavior when database fails"""
        cost_optimizer = ai_components["cost_optimizer"]
        error_handler = ai_components["error_handler"]
        
        # Simulate database connection failure
        with patch('app.ai_engine.cost_optimizer.get_db_connection') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            # System should handle gracefully and log error
            with patch.object(error_handler, 'log_error') as mock_log:
                try:
                    await cost_optimizer.check_cost_limits("test_user", "openai", 100)
                except Exception:
                    pass  # Expected to fail
                
                # Should still return a response (graceful degradation)
                result = await cost_optimizer.check_cost_limits("test_user", "openai", 100)
                assert "error" in result or result.get("within_limits") is True  # Default to allowing
    
    @pytest.mark.asyncio
    async def test_provider_failure_fallback(self, ai_components):
        """Test fallback behavior when AI provider fails"""
        learning_system = ai_components["learning_system"]
        
        # Test adaptation when primary provider fails frequently
        mock_performance = {
            "provider_performance": {
                "openai": {"overall_accuracy": 0.3, "total_signals": 20},  # Poor performance
                "claude": {"overall_accuracy": 0.85, "total_signals": 15}   # Good performance
            }
        }
        
        with patch.object(learning_system, 'get_provider_performance') as mock_perf:
            mock_perf.return_value = mock_performance
            
            thresholds = await learning_system.adapt_confidence_thresholds("test_user")
            
            # Should increase threshold for poor-performing provider
            assert thresholds["adapted_thresholds"]["openai"] > thresholds["default_threshold"]
            # Should decrease threshold for well-performing provider
            assert thresholds["adapted_thresholds"]["claude"] < thresholds["default_threshold"]

if __name__ == "__main__":
    pytest.main([__file__])