"""
Test suite for Learning System
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from app.ai_engine.learning_system import LearningSystem, FeedbackType, OutcomeType

@pytest.fixture
def learning_system():
    """Create a LearningSystem instance for testing"""
    return LearningSystem()

@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    with patch('app.ai_engine.learning_system.get_db_connection') as mock:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_cursor

class TestLearningSystem:
    """Test cases for LearningSystem"""
    
    @pytest.mark.asyncio
    async def test_record_feedback_success(self, learning_system, mock_db_connection):
        """Test successful feedback recording"""
        mock_db_connection.lastrowid = 123
        
        with patch.object(learning_system, 'update_user_preferences') as mock_update:
            mock_update.return_value = None
            
            result = await learning_system.record_feedback(
                "test_user",
                FeedbackType.SIGNAL_ACCURACY,
                "signal_123",
                4,
                "Good signal",
                {"provider_used": "openai"}
            )
            
            assert result is True
            mock_db_connection.execute.assert_called()
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_trade_outcome_success(self, learning_system, mock_db_connection):
        """Test successful trade outcome recording"""
        mock_db_connection.lastrowid = 456
        
        with patch.object(learning_system, 'update_signal_accuracy') as mock_update:
            mock_update.return_value = None
            
            result = await learning_system.record_trade_outcome(
                "test_user",
                "signal_123",
                OutcomeType.PROFIT,
                500.0,
                100.50,
                {"execution_time": "2025-07-21T10:30:00Z"}
            )
            
            assert result is True
            mock_db_connection.execute.assert_called()
            mock_update.assert_called_once()
    
    def test_calculate_accuracy_score_buy_profit(self, learning_system):
        """Test accuracy score calculation for profitable buy signal"""
        score = learning_system.calculate_accuracy_score(OutcomeType.PROFIT, 1000.0, "buy")
        assert score > 0.5  # Should be above neutral
        assert score <= 1.0
    
    def test_calculate_accuracy_score_buy_loss(self, learning_system):
        """Test accuracy score calculation for losing buy signal"""
        score = learning_system.calculate_accuracy_score(OutcomeType.LOSS, -500.0, "buy")
        assert score < 0.5  # Should be below neutral
        assert score >= 0.0
    
    def test_calculate_accuracy_score_cancelled(self, learning_system):
        """Test accuracy score calculation for cancelled trade"""
        score = learning_system.calculate_accuracy_score(OutcomeType.CANCELLED, 0.0, "buy")
        assert score == 0.5  # Neutral score
    
    def test_calculate_accuracy_score_hold(self, learning_system):
        """Test accuracy score calculation for hold signal"""
        # Small movement - good hold signal
        score = learning_system.calculate_accuracy_score(OutcomeType.PROFIT, 50.0, "hold")
        assert score == 0.7
        
        # Large movement - poor hold signal
        score = learning_system.calculate_accuracy_score(OutcomeType.PROFIT, 500.0, "hold")
        assert score == 0.3
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_good_feedback(self, learning_system, mock_db_connection):
        """Test user preference updates with good feedback"""
        # Mock existing preferences
        mock_db_connection.fetchone.return_value = (
            '{"signals": ["claude", "openai"]}',  # provider_priorities
            "medium",  # risk_tolerance
            "balanced"  # trading_style
        )
        
        await learning_system.update_user_preferences(
            "test_user",
            FeedbackType.SIGNAL_ACCURACY,
            5,  # Excellent rating
            {"provider_used": "openai"}
        )
        
        # Should update preferences
        mock_db_connection.execute.assert_called()
        update_call = mock_db_connection.execute.call_args_list[-1]
        assert "UPDATE ai_user_preferences" in update_call[0][0]
    
    @pytest.mark.asyncio
    async def test_update_signal_accuracy(self, learning_system, mock_db_connection):
        """Test signal accuracy tracking update"""
        # Mock signal details
        mock_db_connection.fetchone.side_effect = [
            (0.8, "openai", "buy"),  # Signal details
        ]
        
        await learning_system.update_signal_accuracy(
            "test_user",
            "signal_123",
            OutcomeType.PROFIT,
            750.0
        )
        
        # Should insert accuracy tracking record
        mock_db_connection.execute.assert_called()
        insert_calls = [call for call in mock_db_connection.execute.call_args_list 
                       if "INSERT INTO ai_accuracy_tracking" in str(call)]
        assert len(insert_calls) > 0
    
    @pytest.mark.asyncio
    async def test_get_provider_performance(self, learning_system, mock_db_connection):
        """Test provider performance metrics retrieval"""
        # Mock accuracy data
        accuracy_data = [
            ("openai", "buy", 0.75, 0.8, 10, 5000),
            ("claude", "buy", 0.85, 0.9, 8, 4000),
            ("openai", "sell", 0.65, 0.7, 5, 2000)
        ]
        
        # Mock feedback data
        feedback_data = [
            ("signal_accuracy", 4.2, 15),
            ("analysis_quality", 3.8, 10)
        ]
        
        mock_db_connection.fetchall.side_effect = [accuracy_data, feedback_data]
        
        result = await learning_system.get_provider_performance("test_user", 30)
        
        assert result["user_id"] == "test_user"
        assert result["analysis_period_days"] == 30
        assert "provider_performance" in result
        assert "feedback_summary" in result
        
        # Check provider performance structure
        provider_perf = result["provider_performance"]
        assert "openai" in provider_perf
        assert "claude" in provider_perf
        
        # OpenAI should have both buy and sell data
        assert "buy" in provider_perf["openai"]["signal_types"]
        assert "sell" in provider_perf["openai"]["signal_types"]
        assert provider_perf["openai"]["total_signals"] == 15  # 10 + 5
        assert provider_perf["openai"]["total_pnl"] == 7000  # 5000 + 2000
    
    @pytest.mark.asyncio
    async def test_get_learning_insights(self, learning_system):
        """Test learning insights generation"""
        mock_performance = {
            "provider_performance": {
                "openai": {
                    "overall_accuracy": 0.75,
                    "signal_types": {
                        "buy": {"avg_accuracy": 0.8, "signal_count": 10}
                    }
                },
                "claude": {
                    "overall_accuracy": 0.85,
                    "signal_types": {
                        "buy": {"avg_accuracy": 0.9, "signal_count": 8}
                    }
                }
            },
            "feedback_summary": {
                "signal_accuracy": {"feedback_count": 10}
            }
        }
        
        with patch.object(learning_system, 'get_provider_performance') as mock_perf:
            mock_perf.return_value = mock_performance
            
            result = await learning_system.get_learning_insights("test_user")
            
            assert result["user_id"] == "test_user"
            assert "insights" in result
            assert "recommendations" in result
            assert "learning_status" in result
            
            # Should identify Claude as best provider
            best_provider_insight = next(
                (insight for insight in result["insights"] if insight["type"] == "best_provider"),
                None
            )
            assert best_provider_insight is not None
            assert "claude" in best_provider_insight["message"].lower()
    
    @pytest.mark.asyncio
    async def test_adapt_confidence_thresholds(self, learning_system):
        """Test confidence threshold adaptation"""
        mock_performance = {
            "provider_performance": {
                "openai": {
                    "overall_accuracy": 0.85,  # High accuracy
                    "total_signals": 20
                },
                "claude": {
                    "overall_accuracy": 0.55,  # Low accuracy
                    "total_signals": 15
                },
                "gemini": {
                    "overall_accuracy": 0.7,  # Average accuracy
                    "total_signals": 10
                }
            }
        }
        
        with patch.object(learning_system, 'get_provider_performance') as mock_perf:
            mock_perf.return_value = mock_performance
            
            result = await learning_system.adapt_confidence_thresholds("test_user")
            
            assert result["user_id"] == "test_user"
            assert "adapted_thresholds" in result
            
            thresholds = result["adapted_thresholds"]
            
            # OpenAI should have lower threshold (high accuracy)
            assert thresholds["openai"] < learning_system.confidence_threshold
            
            # Claude should have higher threshold (low accuracy)
            assert thresholds["claude"] > learning_system.confidence_threshold
            
            # Gemini should have default threshold (average accuracy)
            assert thresholds["gemini"] == learning_system.confidence_threshold

class TestLearningSystemIntegration:
    """Integration tests for LearningSystem"""
    
    @pytest.mark.asyncio
    async def test_feedback_to_adaptation_workflow(self, learning_system, mock_db_connection):
        """Test complete feedback to adaptation workflow"""
        # Mock database responses for preference updates
        mock_db_connection.fetchone.side_effect = [
            ('{"signals": ["openai"]}', "medium", "balanced"),  # Current preferences
            None  # Update result
        ]
        
        # Record positive feedback
        with patch.object(learning_system, 'update_user_preferences') as mock_update:
            result = await learning_system.record_feedback(
                "test_user",
                FeedbackType.SIGNAL_ACCURACY,
                "signal_123",
                5,  # Excellent rating
                "Great signal!",
                {"provider_used": "claude"}
            )
            
            assert result is True
            mock_update.assert_called_once_with(
                "test_user",
                FeedbackType.SIGNAL_ACCURACY,
                5,
                {"provider_used": "claude"}
            )
    
    @pytest.mark.asyncio
    async def test_trade_outcome_to_accuracy_workflow(self, learning_system, mock_db_connection):
        """Test complete trade outcome to accuracy tracking workflow"""
        # Mock signal details
        mock_db_connection.fetchone.side_effect = [
            (0.8, "openai", "buy"),  # Signal details for accuracy update
        ]
        
        with patch.object(learning_system, 'update_signal_accuracy') as mock_update:
            result = await learning_system.record_trade_outcome(
                "test_user",
                "signal_123",
                OutcomeType.PROFIT,
                1000.0,
                105.50
            )
            
            assert result is True
            mock_update.assert_called_once_with(
                "test_user",
                "signal_123",
                OutcomeType.PROFIT,
                1000.0
            )
    
    @pytest.mark.asyncio
    async def test_learning_system_with_insufficient_data(self, learning_system):
        """Test learning system behavior with insufficient data"""
        mock_performance = {
            "provider_performance": {
                "openai": {
                    "total_signals": 2,  # Below minimum threshold
                    "overall_accuracy": 0.9
                }
            },
            "feedback_summary": {
                "signal_accuracy": {"feedback_count": 3}  # Below minimum
            }
        }
        
        with patch.object(learning_system, 'get_provider_performance') as mock_perf:
            mock_perf.return_value = mock_performance
            
            insights = await learning_system.get_learning_insights("test_user")
            
            # Should indicate learning is not active
            assert insights["learning_status"]["learning_active"] is False
            assert insights["learning_status"]["total_feedback"] == 3
            
            # Should recommend more feedback
            recommendations = insights["recommendations"]
            feedback_rec = next(
                (rec for rec in recommendations if "feedback" in rec.lower()),
                None
            )
            assert feedback_rec is not None

if __name__ == "__main__":
    pytest.main([__file__])