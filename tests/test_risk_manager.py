"""
Test suite for Risk Manager
"""
import pytest
from unittest.mock import Mock, patch
from app.ai_engine.risk_manager import RiskManager, RiskLevel, RiskType

@pytest.fixture
def risk_manager():
    """Create a RiskManager instance for testing"""
    return RiskManager()

@pytest.fixture
def sample_portfolio():
    """Sample portfolio data for testing"""
    return {
        "total_value": 1000000,  # 10L
        "holdings": [
            {"symbol": "RELIANCE", "current_value": 200000, "sector": "Energy"},
            {"symbol": "TCS", "current_value": 150000, "sector": "IT"},
            {"symbol": "HDFCBANK", "current_value": 120000, "sector": "Banking"},
            {"symbol": "INFY", "current_value": 100000, "sector": "IT"},
            {"symbol": "ICICIBANK", "current_value": 80000, "sector": "Banking"},
            {"symbol": "WIPRO", "current_value": 70000, "sector": "IT"},
            {"symbol": "SBIN", "current_value": 60000, "sector": "Banking"},
            {"symbol": "BHARTIARTL", "current_value": 50000, "sector": "Telecom"},
            {"symbol": "MARUTI", "current_value": 40000, "sector": "Auto"},
            {"symbol": "ASIANPAINT", "current_value": 30000, "sector": "Paints"}
        ]
    }

class TestRiskManager:
    """Test cases for RiskManager"""
    
    @pytest.mark.asyncio
    async def test_assess_portfolio_risk_balanced(self, risk_manager, sample_portfolio):
        """Test portfolio risk assessment for balanced portfolio"""
        result = await risk_manager.assess_portfolio_risk("test_user", sample_portfolio)
        
        assert result["user_id"] == "test_user"
        assert result["overall_risk"] in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert "risk_factors" in result
        assert "recommendations" in result
        assert result["portfolio_summary"]["total_value"] == 1000000
        assert result["portfolio_summary"]["holdings_count"] == 10
    
    def test_assess_concentration_risk_low(self, risk_manager):
        """Test concentration risk assessment - low risk"""
        holdings = [
            {"symbol": "STOCK1", "current_value": 50000},
            {"symbol": "STOCK2", "current_value": 50000},
            {"symbol": "STOCK3", "current_value": 50000}
        ]
        total_value = 1000000
        
        result = risk_manager.assess_concentration_risk(holdings, total_value)
        
        assert result["risk_level"] == RiskLevel.LOW
        assert result["max_concentration"] == 0.05  # 5%
        assert len(result["high_concentration_positions"]) == 0
    
    def test_assess_concentration_risk_high(self, risk_manager):
        """Test concentration risk assessment - high risk"""
        holdings = [
            {"symbol": "STOCK1", "current_value": 300000},  # 30%
            {"symbol": "STOCK2", "current_value": 50000}
        ]
        total_value = 1000000
        
        result = risk_manager.assess_concentration_risk(holdings, total_value)
        
        assert result["risk_level"] == RiskLevel.CRITICAL
        assert result["max_concentration"] == 0.3
        assert len(result["high_concentration_positions"]) == 1
        assert result["high_concentration_positions"][0]["symbol"] == "STOCK1"
    
    def test_assess_sector_risk_balanced(self, risk_manager):
        """Test sector risk assessment - balanced"""
        holdings = [
            {"symbol": "STOCK1", "current_value": 100000, "sector": "IT"},
            {"symbol": "STOCK2", "current_value": 100000, "sector": "Banking"},
            {"symbol": "STOCK3", "current_value": 100000, "sector": "Energy"},
            {"symbol": "STOCK4", "current_value": 100000, "sector": "Auto"}
        ]
        total_value = 1000000
        
        result = risk_manager.assess_sector_risk(holdings, total_value)
        
        assert result["risk_level"] == RiskLevel.LOW
        assert result["max_sector_allocation"] == 0.1  # 10% each
        assert len(result["high_concentration_sectors"]) == 0
    
    def test_assess_sector_risk_concentrated(self, risk_manager):
        """Test sector risk assessment - concentrated"""
        holdings = [
            {"symbol": "STOCK1", "current_value": 200000, "sector": "IT"},
            {"symbol": "STOCK2", "current_value": 200000, "sector": "IT"},
            {"symbol": "STOCK3", "current_value": 100000, "sector": "IT"}
        ]
        total_value = 1000000
        
        result = risk_manager.assess_sector_risk(holdings, total_value)
        
        assert result["risk_level"] == RiskLevel.CRITICAL  # 50% in IT
        assert result["max_sector_allocation"] == 0.5
        assert len(result["high_concentration_sectors"]) == 1
        assert result["high_concentration_sectors"][0]["sector"] == "IT"
    
    def test_assess_position_size_risk_normal(self, risk_manager):
        """Test position size risk assessment - normal"""
        holdings = [
            {"symbol": "STOCK1", "current_value": 80000},  # 8%
            {"symbol": "STOCK2", "current_value": 70000},  # 7%
            {"symbol": "STOCK3", "current_value": 60000}   # 6%
        ]
        total_value = 1000000
        
        result = risk_manager.assess_position_size_risk(holdings, total_value)
        
        assert result["risk_level"] == RiskLevel.LOW
        assert len(result["oversized_positions"]) == 0
        assert result["avg_position_size"] == 0.07  # 7% average
    
    def test_assess_position_size_risk_oversized(self, risk_manager):
        """Test position size risk assessment - oversized positions"""
        holdings = [
            {"symbol": "STOCK1", "current_value": 150000},  # 15%
            {"symbol": "STOCK2", "current_value": 120000},  # 12%
            {"symbol": "STOCK3", "current_value": 110000}   # 11%
        ]
        total_value = 1000000
        
        result = risk_manager.assess_position_size_risk(holdings, total_value)
        
        assert result["risk_level"] == RiskLevel.HIGH  # Multiple oversized positions
        assert len(result["oversized_positions"]) == 3
        assert result["recommended_max_size"] == risk_manager.max_position_size
    
    def test_calculate_overall_risk_multiple_factors(self, risk_manager):
        """Test overall risk calculation with multiple factors"""
        risk_factors = [
            {"risk_level": RiskLevel.HIGH},
            {"risk_level": RiskLevel.MEDIUM},
            {"risk_level": RiskLevel.LOW}
        ]
        
        result = risk_manager.calculate_overall_risk(risk_factors)
        assert result == RiskLevel.HIGH
        
        # Test critical risk
        risk_factors[0]["risk_level"] = RiskLevel.CRITICAL
        result = risk_manager.calculate_overall_risk(risk_factors)
        assert result == RiskLevel.CRITICAL
        
        # Test multiple medium risks
        risk_factors = [
            {"risk_level": RiskLevel.MEDIUM},
            {"risk_level": RiskLevel.MEDIUM}
        ]
        result = risk_manager.calculate_overall_risk(risk_factors)
        assert result == RiskLevel.HIGH
    
    def test_calculate_risk_score(self, risk_manager):
        """Test risk score calculation"""
        # No risk factors
        assert risk_manager.calculate_risk_score([]) == 10
        
        # Single critical risk
        risk_factors = [{"risk_level": RiskLevel.CRITICAL}]
        assert risk_manager.calculate_risk_score(risk_factors) == 40  # 10 + 30
        
        # Multiple risks
        risk_factors = [
            {"risk_level": RiskLevel.HIGH},
            {"risk_level": RiskLevel.MEDIUM},
            {"risk_level": RiskLevel.LOW}
        ]
        assert risk_manager.calculate_risk_score(risk_factors) == 45  # 10 + 20 + 10 + 5
    
    def test_calculate_diversification_score(self, risk_manager, sample_portfolio):
        """Test diversification score calculation"""
        score = risk_manager.calculate_diversification_score(sample_portfolio["holdings"])
        
        assert 0 <= score <= 100
        assert score > 50  # Should be reasonably diversified
        
        # Test empty portfolio
        assert risk_manager.calculate_diversification_score([]) == 0
        
        # Test single holding
        single_holding = [{"symbol": "STOCK1", "current_value": 100000, "sector": "IT"}]
        score = risk_manager.calculate_diversification_score(single_holding)
        assert score < 30  # Should be low diversification
    
    @pytest.mark.asyncio
    async def test_get_position_size_recommendation(self, risk_manager):
        """Test position size recommendation"""
        result = await risk_manager.get_position_size_recommendation(
            "test_user", "RELIANCE", 1000000, "medium"
        )
        
        assert result["symbol"] == "RELIANCE"
        assert result["recommended_position_size"] <= risk_manager.max_position_size
        assert result["recommended_amount"] == result["recommended_position_size"] * 1000000
        assert result["risk_tolerance"] == "medium"
        
        # Test high risk tolerance
        result_high = await risk_manager.get_position_size_recommendation(
            "test_user", "RELIANCE", 1000000, "high"
        )
        assert result_high["recommended_position_size"] > result["recommended_position_size"]
        
        # Test low risk tolerance
        result_low = await risk_manager.get_position_size_recommendation(
            "test_user", "RELIANCE", 1000000, "low"
        )
        assert result_low["recommended_position_size"] < result["recommended_position_size"]
    
    @pytest.mark.asyncio
    async def test_validate_trade_risk_approved(self, risk_manager, sample_portfolio):
        """Test trade risk validation - approved trade"""
        trade_data = {
            "symbol": "NEWSTOCK",
            "amount": 50000,  # 5% of portfolio
            "type": "buy"
        }
        
        result = await risk_manager.validate_trade_risk("test_user", trade_data, sample_portfolio)
        
        assert result["approved"] is True
        assert result["position_size"] == 0.05
        assert result["risk_level"] == "low"
    
    @pytest.mark.asyncio
    async def test_validate_trade_risk_rejected_size(self, risk_manager, sample_portfolio):
        """Test trade risk validation - rejected due to size"""
        trade_data = {
            "symbol": "NEWSTOCK",
            "amount": 200000,  # 20% of portfolio - too large
            "type": "buy"
        }
        
        result = await risk_manager.validate_trade_risk("test_user", trade_data, sample_portfolio)
        
        assert result["approved"] is False
        assert "exceeds maximum allowed" in result["reason"]
        assert "recommended_amount" in result
    
    @pytest.mark.asyncio
    async def test_validate_trade_risk_existing_position(self, risk_manager, sample_portfolio):
        """Test trade risk validation - adding to existing position"""
        trade_data = {
            "symbol": "RELIANCE",  # Already exists with 200000 (20%)
            "amount": 50000,  # Would make total 25%
            "type": "buy"
        }
        
        result = await risk_manager.validate_trade_risk("test_user", trade_data, sample_portfolio)
        
        assert result["approved"] is False
        assert "Combined position size" in result["reason"]
        assert result["current_position_value"] == 200000

class TestRiskManagerIntegration:
    """Integration tests for RiskManager"""
    
    @pytest.mark.asyncio
    async def test_full_portfolio_assessment_workflow(self, risk_manager):
        """Test complete portfolio assessment workflow"""
        # Create a risky portfolio
        risky_portfolio = {
            "total_value": 1000000,
            "holdings": [
                {"symbol": "STOCK1", "current_value": 300000, "sector": "IT"},  # 30% concentration
                {"symbol": "STOCK2", "current_value": 250000, "sector": "IT"},  # 25% concentration
                {"symbol": "STOCK3", "current_value": 200000, "sector": "IT"},  # 20% concentration
                {"symbol": "STOCK4", "current_value": 150000, "sector": "Banking"},  # 15%
                {"symbol": "STOCK5", "current_value": 100000, "sector": "Banking"}   # 10%
            ]
        }
        
        result = await risk_manager.assess_portfolio_risk("test_user", risky_portfolio)
        
        # Should identify multiple risk factors
        assert result["overall_risk"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(result["risk_factors"]) >= 2  # Concentration and sector risks
        assert len(result["recommendations"]) > 0
        assert result["risk_score"] > 50  # High risk score
        
        # Check specific risk factors
        risk_types = [factor["risk_type"] for factor in result["risk_factors"]]
        assert RiskType.CONCENTRATION in risk_types
        assert RiskType.SECTOR in risk_types

if __name__ == "__main__":
    pytest.main([__file__])