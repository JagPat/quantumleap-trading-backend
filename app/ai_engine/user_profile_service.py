"""
User Investment Profile Service
Manages user investment preferences, risk tolerance, and personalized settings
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class UserProfileService:
    """Service for managing user investment profiles and preferences"""
    
    def __init__(self):
        self.default_profile = {
            "risk_tolerance": "moderate",  # Database compatible
            "investment_timeline": "medium_term",
            "preferred_sectors": [],
            "max_position_size": 15.0,
            "min_position_size": 2.0,
            "trading_frequency": "monthly",  # Database compatible
            "auto_trading_enabled": False,
            "stop_loss_preference": 10.0,
            "take_profit_preference": 20.0,
            "diversification_preference": "balanced",
            "esg_preference": False,
            "dividend_preference": "reinvest",  # Database compatible
            "growth_vs_value": "balanced"
        }
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user investment profile
        Args:
            user_id: User identifier
        Returns:
            Dictionary with user investment profile
        """
        try:
            # Get profile from database
            from app.database.service import get_user_investment_profile
            db_profile = get_user_investment_profile(user_id)
            
            if db_profile:
                # Merge with defaults for any missing fields
                profile = self.default_profile.copy()
                profile.update(db_profile)
                
                # Add computed fields
                profile["profile_completeness"] = self._calculate_profile_completeness(profile)
                profile["risk_score"] = self._calculate_risk_score(profile)
                profile["last_updated"] = db_profile.get("updated_at", datetime.now().isoformat())
                
                logger.info(f"Retrieved user profile for {user_id} with {profile['profile_completeness']:.0f}% completeness")
                return profile
            else:
                # Return default profile for new users
                logger.info(f"No profile found for user {user_id}, returning default profile")
                return self._create_default_profile(user_id)
                
        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}")
            return self._create_default_profile(user_id)
    
    async def update_user_profile(
        self, 
        user_id: str, 
        profile_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user investment profile
        Args:
            user_id: User identifier
            profile_updates: Dictionary with profile updates
        Returns:
            Updated profile dictionary
        """
        try:
            # Validate profile updates
            validated_updates = self._validate_profile_updates(profile_updates)
            
            # Get current profile
            current_profile = await self.get_user_profile(user_id)
            
            # Merge updates
            updated_profile = current_profile.copy()
            updated_profile.update(validated_updates)
            updated_profile["updated_at"] = datetime.now().isoformat()
            
            # Save to database
            from app.database.service import save_user_investment_profile
            success = save_user_investment_profile(user_id, updated_profile)
            
            if success:
                # Recalculate computed fields
                updated_profile["profile_completeness"] = self._calculate_profile_completeness(updated_profile)
                updated_profile["risk_score"] = self._calculate_risk_score(updated_profile)
                
                logger.info(f"Updated user profile for {user_id}")
                return updated_profile
            else:
                logger.error(f"Failed to save profile updates for user {user_id}")
                return current_profile
                
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}")
            # Return current profile on error
            return await self.get_user_profile(user_id)
    
    async def get_profile_recommendations(self, user_id: str) -> Dict[str, Any]:
        """
        Get personalized recommendations based on user profile
        Args:
            user_id: User identifier
        Returns:
            Dictionary with personalized recommendations
        """
        try:
            profile = await self.get_user_profile(user_id)
            
            recommendations = {
                "sector_allocation": self._get_sector_allocation_recommendations(profile),
                "risk_management": self._get_risk_management_recommendations(profile),
                "trading_strategy": self._get_trading_strategy_recommendations(profile),
                "portfolio_optimization": self._get_portfolio_optimization_recommendations(profile),
                "profile_improvements": self._get_profile_improvement_suggestions(profile)
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get profile recommendations for {user_id}: {e}")
            return {}
    
    def _create_default_profile(self, user_id: str) -> Dict[str, Any]:
        """Create default profile for new user"""
        profile = self.default_profile.copy()
        profile.update({
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "profile_completeness": 30.0,  # Basic default completeness
            "risk_score": 50.0,  # Neutral risk score
            "is_new_profile": True
        })
        return profile
    
    def _validate_profile_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize profile updates"""
        validated = {}
        
        # Risk tolerance validation
        if "risk_tolerance" in updates:
            valid_risk_levels = ["conservative", "moderate", "medium", "aggressive", "high"]
            if updates["risk_tolerance"] in valid_risk_levels:
                validated["risk_tolerance"] = updates["risk_tolerance"]
        
        # Investment timeline validation
        if "investment_timeline" in updates:
            valid_timelines = ["short_term", "medium_term", "long_term"]
            if updates["investment_timeline"] in valid_timelines:
                validated["investment_timeline"] = updates["investment_timeline"]
        
        # Preferred sectors validation
        if "preferred_sectors" in updates:
            valid_sectors = [
                "Technology", "Banking", "Pharmaceuticals", "FMCG", "Energy",
                "Automotive", "Infrastructure", "Telecom", "Real Estate", "Metals"
            ]
            if isinstance(updates["preferred_sectors"], list):
                validated["preferred_sectors"] = [
                    sector for sector in updates["preferred_sectors"] 
                    if sector in valid_sectors
                ]
        
        # Position size validation
        if "max_position_size" in updates:
            try:
                max_size = float(updates["max_position_size"])
                if 5.0 <= max_size <= 50.0:  # Reasonable limits
                    validated["max_position_size"] = max_size
            except (ValueError, TypeError):
                pass
        
        if "min_position_size" in updates:
            try:
                min_size = float(updates["min_position_size"])
                if 0.5 <= min_size <= 10.0:  # Reasonable limits
                    validated["min_position_size"] = min_size
            except (ValueError, TypeError):
                pass
        
        # Trading frequency validation (match database constraints)
        if "trading_frequency" in updates:
            # Map user-friendly values to database values
            frequency_mapping = {
                "low": "monthly",
                "moderate": "weekly", 
                "high": "daily",
                "very_high": "daily",
                "daily": "daily",
                "weekly": "weekly",
                "monthly": "monthly",
                "quarterly": "quarterly"
            }
            
            user_frequency = updates["trading_frequency"]
            if user_frequency in frequency_mapping:
                validated["trading_frequency"] = frequency_mapping[user_frequency]
        
        # Boolean field validation
        boolean_fields = [
            "auto_trading_enabled", "esg_preference"
        ]
        for field in boolean_fields:
            if field in updates and isinstance(updates[field], bool):
                validated[field] = updates[field]
        
        # Percentage field validation
        percentage_fields = ["stop_loss_preference", "take_profit_preference"]
        for field in percentage_fields:
            if field in updates:
                try:
                    value = float(updates[field])
                    if 1.0 <= value <= 50.0:  # Reasonable percentage limits
                        validated[field] = value
                except (ValueError, TypeError):
                    pass
        
        # Preference validation
        preference_fields = ["diversification_preference", "dividend_preference", "growth_vs_value"]
        valid_preferences = ["conservative", "balanced", "aggressive"]
        for field in preference_fields:
            if field in updates and updates[field] in valid_preferences:
                validated[field] = updates[field]
        
        return validated
    
    def _calculate_profile_completeness(self, profile: Dict[str, Any]) -> float:
        """Calculate profile completeness percentage"""
        try:
            total_fields = 0
            completed_fields = 0
            
            # Core fields (higher weight)
            core_fields = [
                "risk_tolerance", "investment_timeline", "max_position_size",
                "trading_frequency", "diversification_preference"
            ]
            
            for field in core_fields:
                total_fields += 2  # Double weight for core fields
                if profile.get(field) and profile[field] != self.default_profile.get(field):
                    completed_fields += 2
            
            # Optional fields (normal weight)
            optional_fields = [
                "preferred_sectors", "auto_trading_enabled", "stop_loss_preference",
                "take_profit_preference", "esg_preference", "dividend_preference",
                "growth_vs_value"
            ]
            
            for field in optional_fields:
                total_fields += 1
                if field == "preferred_sectors":
                    if profile.get(field) and len(profile[field]) > 0:
                        completed_fields += 1
                elif profile.get(field) is not None:
                    completed_fields += 1
            
            return min(100.0, (completed_fields / total_fields) * 100) if total_fields > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Failed to calculate profile completeness: {e}")
            return 50.0
    
    def _calculate_risk_score(self, profile: Dict[str, Any]) -> float:
        """Calculate numerical risk score (0-100)"""
        try:
            risk_score = 50.0  # Start with neutral
            
            # Risk tolerance impact (40% weight)
            risk_tolerance = profile.get("risk_tolerance", "medium")
            risk_mapping = {
                "conservative": 20,
                "moderate": 35,
                "medium": 50,
                "aggressive": 75,
                "high": 90
            }
            risk_score = risk_mapping.get(risk_tolerance, 50) * 0.4
            
            # Investment timeline impact (20% weight)
            timeline = profile.get("investment_timeline", "medium_term")
            timeline_mapping = {
                "short_term": 70,  # Higher risk for short term
                "medium_term": 50,
                "long_term": 30   # Lower risk for long term
            }
            risk_score += timeline_mapping.get(timeline, 50) * 0.2
            
            # Position size impact (20% weight)
            max_position = profile.get("max_position_size", 15.0)
            position_risk = min(100, max_position * 4)  # Scale to 0-100
            risk_score += position_risk * 0.2
            
            # Trading frequency impact (20% weight)
            frequency = profile.get("trading_frequency", "monthly")
            frequency_mapping = {
                "quarterly": 20,
                "monthly": 35,
                "weekly": 60,
                "daily": 85,
                # Legacy mappings for backward compatibility
                "low": 25,
                "moderate": 50,
                "high": 75,
                "very_high": 90
            }
            risk_score += frequency_mapping.get(frequency, 50) * 0.2
            
            return min(100.0, max(0.0, risk_score))
            
        except Exception as e:
            logger.warning(f"Failed to calculate risk score: {e}")
            return 50.0
    
    def _get_sector_allocation_recommendations(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get sector allocation recommendations based on profile"""
        risk_tolerance = profile.get("risk_tolerance", "medium")
        preferred_sectors = profile.get("preferred_sectors", [])
        
        recommendations = []
        
        if risk_tolerance in ["conservative", "moderate"]:
            recommendations.extend([
                {
                    "sector": "Banking",
                    "recommended_allocation": "15-25%",
                    "reason": "Stable returns and dividend yield suitable for conservative investors"
                },
                {
                    "sector": "FMCG",
                    "recommended_allocation": "10-20%",
                    "reason": "Defensive sector with consistent performance"
                }
            ])
        
        if risk_tolerance in ["medium", "aggressive", "high"]:
            recommendations.extend([
                {
                    "sector": "Technology",
                    "recommended_allocation": "20-30%",
                    "reason": "High growth potential suitable for higher risk tolerance"
                },
                {
                    "sector": "Pharmaceuticals",
                    "recommended_allocation": "10-15%",
                    "reason": "Growth sector with export potential"
                }
            ])
        
        # Add preferred sectors with higher allocation
        for sector in preferred_sectors:
            if not any(rec["sector"] == sector for rec in recommendations):
                recommendations.append({
                    "sector": sector,
                    "recommended_allocation": "10-20%",
                    "reason": f"Matches your sector preference for {sector}"
                })
        
        return recommendations
    
    def _get_risk_management_recommendations(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get risk management recommendations"""
        risk_score = profile.get("risk_score", 50.0)
        max_position = profile.get("max_position_size", 15.0)
        
        recommendations = []
        
        if risk_score > 70:
            recommendations.append({
                "type": "position_sizing",
                "recommendation": f"Consider reducing maximum position size from {max_position}% to 10-12%",
                "reason": "High risk profile suggests need for better diversification"
            })
        
        if not profile.get("stop_loss_preference"):
            recommendations.append({
                "type": "stop_loss",
                "recommendation": "Set stop-loss preferences (suggested: 8-12% for most stocks)",
                "reason": "Automated risk management helps protect capital"
            })
        
        if profile.get("auto_trading_enabled") and risk_score > 60:
            recommendations.append({
                "type": "auto_trading",
                "recommendation": "Review auto-trading settings with high risk profile",
                "reason": "Automated trading with high risk tolerance needs careful monitoring"
            })
        
        return recommendations
    
    def _get_trading_strategy_recommendations(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get trading strategy recommendations"""
        timeline = profile.get("investment_timeline", "medium_term")
        frequency = profile.get("trading_frequency", "moderate")
        
        recommendations = []
        
        if timeline == "long_term" and frequency == "high":
            recommendations.append({
                "strategy": "rebalancing",
                "recommendation": "Consider quarterly rebalancing instead of frequent trading",
                "reason": "Long-term timeline conflicts with high trading frequency"
            })
        
        if timeline == "short_term":
            recommendations.append({
                "strategy": "momentum",
                "recommendation": "Focus on momentum and technical analysis strategies",
                "reason": "Short-term timeline benefits from technical trading approaches"
            })
        
        if profile.get("dividend_preference") == "aggressive":
            recommendations.append({
                "strategy": "dividend_growth",
                "recommendation": "Consider dividend growth stocks over high-yield stocks",
                "reason": "Dividend growth provides better long-term returns"
            })
        
        return recommendations
    
    def _get_portfolio_optimization_recommendations(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get portfolio optimization recommendations"""
        diversification = profile.get("diversification_preference", "balanced")
        growth_vs_value = profile.get("growth_vs_value", "balanced")
        
        recommendations = []
        
        if diversification == "conservative":
            recommendations.append({
                "optimization": "diversification",
                "recommendation": "Maintain positions in at least 15-20 different stocks across 6+ sectors",
                "reason": "Conservative diversification reduces portfolio volatility"
            })
        
        if growth_vs_value == "growth":
            recommendations.append({
                "optimization": "growth_focus",
                "recommendation": "Allocate 60-70% to growth stocks, 30-40% to value stocks",
                "reason": "Growth preference suggests higher allocation to growth companies"
            })
        
        if profile.get("esg_preference"):
            recommendations.append({
                "optimization": "esg_integration",
                "recommendation": "Consider ESG-focused stocks and funds for 20-30% of portfolio",
                "reason": "ESG preference can be integrated while maintaining returns"
            })
        
        return recommendations
    
    def _get_profile_improvement_suggestions(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get suggestions for improving profile completeness"""
        completeness = profile.get("profile_completeness", 0)
        suggestions = []
        
        if completeness < 70:
            if not profile.get("preferred_sectors"):
                suggestions.append({
                    "field": "preferred_sectors",
                    "suggestion": "Add 2-3 preferred sectors to get more targeted recommendations",
                    "impact": "Better sector allocation advice"
                })
            
            if not profile.get("stop_loss_preference"):
                suggestions.append({
                    "field": "stop_loss_preference",
                    "suggestion": "Set stop-loss preference for automated risk management",
                    "impact": "Better risk protection"
                })
            
            if profile.get("growth_vs_value") == "balanced":
                suggestions.append({
                    "field": "growth_vs_value",
                    "suggestion": "Specify growth vs value preference for better stock selection",
                    "impact": "More targeted stock recommendations"
                })
        
        return suggestions

# Global instance
user_profile_service = UserProfileService()