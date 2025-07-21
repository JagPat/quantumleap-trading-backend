"""
Risk Manager
Portfolio and trading risk assessment system
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskType(str, Enum):
    """Types of risk"""
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    LIQUIDITY = "liquidity"
    SECTOR = "sector"
    POSITION_SIZE = "position_size"

class RiskManager:
    """
    Risk management system for portfolio and trading decisions
    """
    
    def __init__(self):
        self.max_position_size = 0.1  # 10% max position size
        self.max_sector_allocation = 0.3  # 30% max sector allocation
        self.correlation_threshold = 0.7  # High correlation threshold
        
    async def assess_portfolio_risk(self, user_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive portfolio risk assessment"""
        
        try:
            holdings = portfolio_data.get("holdings", [])
            total_value = portfolio_data.get("total_value", 0)
            
            if not holdings or total_value <= 0:
                return {
                    "overall_risk": RiskLevel.LOW,
                    "risk_factors": [],
                    "recommendations": ["Add holdings to assess portfolio risk"]
                }
            
            risk_factors = []
            recommendations = []
            
            # 1. Concentration Risk
            concentration_risk = self.assess_concentration_risk(holdings, total_value)
            if concentration_risk["risk_level"] != RiskLevel.LOW:
                risk_factors.append(concentration_risk)
                recommendations.extend(concentration_risk.get("recommendations", []))
            
            # 2. Sector Concentration Risk
            sector_risk = self.assess_sector_risk(holdings, total_value)
            if sector_risk["risk_level"] != RiskLevel.LOW:
                risk_factors.append(sector_risk)
                recommendations.extend(sector_risk.get("recommendations", []))
            
            # 3. Position Size Risk
            position_risk = self.assess_position_size_risk(holdings, total_value)
            if position_risk["risk_level"] != RiskLevel.LOW:
                risk_factors.append(position_risk)
                recommendations.extend(position_risk.get("recommendations", []))
            
            # Determine overall risk level
            overall_risk = self.calculate_overall_risk(risk_factors)
            
            # Generate risk score (0-100)
            risk_score = self.calculate_risk_score(risk_factors)
            
            return {
                "user_id": user_id,
                "overall_risk": overall_risk,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": list(set(recommendations)),  # Remove duplicates
                "assessment_date": datetime.now().isoformat(),
                "portfolio_summary": {
                    "total_value": total_value,
                    "holdings_count": len(holdings),
                    "diversification_score": self.calculate_diversification_score(holdings)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to assess portfolio risk for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "overall_risk": RiskLevel.MEDIUM,
                "error": str(e)
            }
    
    def assess_concentration_risk(self, holdings: List[Dict], total_value: float) -> Dict[str, Any]:
        """Assess concentration risk in individual positions"""
        
        high_concentration_positions = []
        max_concentration = 0
        
        for holding in holdings:
            position_value = holding.get("current_value", 0)
            if total_value > 0:
                concentration = position_value / total_value
                max_concentration = max(max_concentration, concentration)
                
                if concentration > self.max_position_size:
                    high_concentration_positions.append({
                        "symbol": holding.get("symbol", "Unknown"),
                        "concentration": concentration,
                        "value": position_value
                    })
        
        # Determine risk level
        if max_concentration > 0.25:  # 25%+
            risk_level = RiskLevel.CRITICAL
        elif max_concentration > 0.15:  # 15%+
            risk_level = RiskLevel.HIGH
        elif max_concentration > self.max_position_size:  # 10%+
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        recommendations = []
        if high_concentration_positions:
            recommendations.append("Consider reducing position sizes in over-concentrated holdings")
            recommendations.append("Diversify portfolio across more positions")
        
        return {
            "risk_type": RiskType.CONCENTRATION,
            "risk_level": risk_level,
            "max_concentration": max_concentration,
            "high_concentration_positions": high_concentration_positions,
            "recommendations": recommendations
        }
    
    def assess_sector_risk(self, holdings: List[Dict], total_value: float) -> Dict[str, Any]:
        """Assess sector concentration risk"""
        
        sector_allocations = {}
        
        for holding in holdings:
            sector = holding.get("sector", "Unknown")
            position_value = holding.get("current_value", 0)
            
            if sector not in sector_allocations:
                sector_allocations[sector] = 0
            sector_allocations[sector] += position_value
        
        # Calculate sector percentages
        sector_percentages = {}
        max_sector_allocation = 0
        high_concentration_sectors = []
        
        for sector, value in sector_allocations.items():
            if total_value > 0:
                percentage = value / total_value
                sector_percentages[sector] = percentage
                max_sector_allocation = max(max_sector_allocation, percentage)
                
                if percentage > self.max_sector_allocation:
                    high_concentration_sectors.append({
                        "sector": sector,
                        "allocation": percentage,
                        "value": value
                    })
        
        # Determine risk level
        if max_sector_allocation > 0.5:  # 50%+
            risk_level = RiskLevel.CRITICAL
        elif max_sector_allocation > 0.4:  # 40%+
            risk_level = RiskLevel.HIGH
        elif max_sector_allocation > self.max_sector_allocation:  # 30%+
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        recommendations = []
        if high_concentration_sectors:
            recommendations.append("Reduce sector concentration by diversifying across industries")
            recommendations.append("Consider adding positions in underrepresented sectors")
        
        return {
            "risk_type": RiskType.SECTOR,
            "risk_level": risk_level,
            "sector_allocations": sector_percentages,
            "max_sector_allocation": max_sector_allocation,
            "high_concentration_sectors": high_concentration_sectors,
            "recommendations": recommendations
        }
    
    def assess_position_size_risk(self, holdings: List[Dict], total_value: float) -> Dict[str, Any]:
        """Assess individual position size risk"""
        
        oversized_positions = []
        position_sizes = []
        
        for holding in holdings:
            position_value = holding.get("current_value", 0)
            if total_value > 0:
                size_ratio = position_value / total_value
                position_sizes.append(size_ratio)
                
                if size_ratio > self.max_position_size:
                    oversized_positions.append({
                        "symbol": holding.get("symbol", "Unknown"),
                        "size_ratio": size_ratio,
                        "recommended_size": self.max_position_size,
                        "excess_amount": position_value - (total_value * self.max_position_size)
                    })
        
        # Calculate position size statistics
        avg_position_size = sum(position_sizes) / len(position_sizes) if position_sizes else 0
        
        # Determine risk level
        if len(oversized_positions) > 3:
            risk_level = RiskLevel.HIGH
        elif len(oversized_positions) > 1:
            risk_level = RiskLevel.MEDIUM
        elif len(oversized_positions) == 1:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        recommendations = []
        if oversized_positions:
            recommendations.append("Reduce position sizes to recommended maximum")
            recommendations.append("Consider partial profit-taking in oversized positions")
        
        return {
            "risk_type": RiskType.POSITION_SIZE,
            "risk_level": risk_level,
            "oversized_positions": oversized_positions,
            "avg_position_size": avg_position_size,
            "recommended_max_size": self.max_position_size,
            "recommendations": recommendations
        }
    
    def calculate_overall_risk(self, risk_factors: List[Dict[str, Any]]) -> str:
        """Calculate overall portfolio risk level"""
        
        if not risk_factors:
            return RiskLevel.LOW
        
        risk_levels = [factor["risk_level"] for factor in risk_factors]
        
        # If any critical risk, overall is critical
        if RiskLevel.CRITICAL in risk_levels:
            return RiskLevel.CRITICAL
        # If multiple high risks or any high risk, overall is high
        elif risk_levels.count(RiskLevel.HIGH) >= 2 or RiskLevel.HIGH in risk_levels:
            return RiskLevel.HIGH
        # If multiple medium risks, overall is high
        elif risk_levels.count(RiskLevel.MEDIUM) >= 2:
            return RiskLevel.HIGH
        # If any medium risk, overall is medium
        elif RiskLevel.MEDIUM in risk_levels:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def calculate_risk_score(self, risk_factors: List[Dict[str, Any]]) -> int:
        """Calculate numerical risk score (0-100)"""
        
        if not risk_factors:
            return 10  # Base risk score
        
        score = 10  # Base score
        
        for factor in risk_factors:
            risk_level = factor["risk_level"]
            if risk_level == RiskLevel.CRITICAL:
                score += 30
            elif risk_level == RiskLevel.HIGH:
                score += 20
            elif risk_level == RiskLevel.MEDIUM:
                score += 10
            else:
                score += 5
        
        return min(score, 100)  # Cap at 100
    
    def calculate_diversification_score(self, holdings: List[Dict]) -> int:
        """Calculate diversification score (0-100)"""
        
        if not holdings:
            return 0
        
        # Base score for having holdings
        score = 20
        
        # Points for number of holdings
        num_holdings = len(holdings)
        if num_holdings >= 20:
            score += 30
        elif num_holdings >= 15:
            score += 25
        elif num_holdings >= 10:
            score += 20
        elif num_holdings >= 5:
            score += 15
        else:
            score += num_holdings * 2
        
        # Points for sector diversity
        sectors = set(holding.get("sector", "Unknown") for holding in holdings)
        num_sectors = len(sectors)
        if num_sectors >= 8:
            score += 25
        elif num_sectors >= 6:
            score += 20
        elif num_sectors >= 4:
            score += 15
        else:
            score += num_sectors * 3
        
        # Penalty for concentration
        total_value = sum(holding.get("current_value", 0) for holding in holdings)
        if total_value > 0:
            max_position = max(holding.get("current_value", 0) / total_value for holding in holdings)
            if max_position > 0.2:  # 20%+
                score -= 15
            elif max_position > 0.15:  # 15%+
                score -= 10
            elif max_position > 0.1:  # 10%+
                score -= 5
        
        return max(0, min(score, 100))
    
    async def get_position_size_recommendation(
        self, 
        user_id: str, 
        symbol: str, 
        portfolio_value: float,
        risk_tolerance: str = "medium"
    ) -> Dict[str, Any]:
        """Get position size recommendation for a new trade"""
        
        try:
            # Risk tolerance multipliers
            risk_multipliers = {
                "low": 0.5,
                "medium": 1.0,
                "high": 1.5
            }
            
            multiplier = risk_multipliers.get(risk_tolerance, 1.0)
            base_position_size = self.max_position_size * multiplier
            
            # Adjust based on portfolio size
            if portfolio_value < 100000:  # Less than 1L
                base_position_size *= 0.8  # Be more conservative
            elif portfolio_value > 1000000:  # More than 10L
                base_position_size *= 1.2  # Can take slightly larger positions
            
            # Cap at maximum
            recommended_size = min(base_position_size, 0.15)  # Never more than 15%
            recommended_amount = portfolio_value * recommended_size
            
            return {
                "symbol": symbol,
                "recommended_position_size": recommended_size,
                "recommended_amount": recommended_amount,
                "max_amount": portfolio_value * self.max_position_size,
                "risk_tolerance": risk_tolerance,
                "reasoning": f"Based on {risk_tolerance} risk tolerance and portfolio size"
            }
            
        except Exception as e:
            logger.error(f"Failed to get position size recommendation: {e}")
            return {
                "symbol": symbol,
                "recommended_position_size": 0.05,  # Conservative default
                "error": str(e)
            }
    
    async def validate_trade_risk(
        self, 
        user_id: str, 
        trade_data: Dict[str, Any],
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate if a proposed trade meets risk criteria"""
        
        try:
            symbol = trade_data.get("symbol")
            trade_amount = trade_data.get("amount", 0)
            trade_type = trade_data.get("type", "buy")
            
            portfolio_value = portfolio_data.get("total_value", 0)
            
            if portfolio_value <= 0:
                return {
                    "approved": False,
                    "reason": "Cannot assess risk without portfolio data"
                }
            
            # Check position size
            position_size = trade_amount / portfolio_value
            
            if position_size > self.max_position_size:
                return {
                    "approved": False,
                    "reason": f"Position size ({position_size:.1%}) exceeds maximum allowed ({self.max_position_size:.1%})",
                    "recommended_amount": portfolio_value * self.max_position_size
                }
            
            # For buy orders, check if it would create concentration
            if trade_type == "buy":
                # Check if symbol already exists in portfolio
                holdings = portfolio_data.get("holdings", [])
                existing_position = next((h for h in holdings if h.get("symbol") == symbol), None)
                
                if existing_position:
                    current_value = existing_position.get("current_value", 0)
                    new_total_value = current_value + trade_amount
                    new_position_size = new_total_value / portfolio_value
                    
                    if new_position_size > self.max_position_size:
                        return {
                            "approved": False,
                            "reason": f"Combined position size would be {new_position_size:.1%}, exceeding maximum",
                            "current_position_value": current_value,
                            "max_additional_amount": (portfolio_value * self.max_position_size) - current_value
                        }
            
            return {
                "approved": True,
                "position_size": position_size,
                "risk_level": "low" if position_size < 0.05 else "medium" if position_size < 0.08 else "high"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate trade risk: {e}")
            return {
                "approved": False,
                "reason": f"Risk validation error: {str(e)}"
            }