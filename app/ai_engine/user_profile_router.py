"""
User Investment Profile API Router
Provides REST endpoints for managing user investment profiles and preferences
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from .user_profile_service import user_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/investment-profile", tags=["User Investment Profile"])

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    return "default_user"

@router.get("/")
async def get_user_profile(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get complete user investment profile"""
    try:
        profile = await user_profile_service.get_user_profile(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "profile": profile,
            "timestamp": datetime.now().isoformat(),
            "message": "User profile retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get user profile for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )

@router.put("/")
async def update_user_profile(
    profile_updates: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Update user investment profile"""
    try:
        updated_profile = await user_profile_service.update_user_profile(
            user_id, profile_updates
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "profile": updated_profile,
            "timestamp": datetime.now().isoformat(),
            "message": "User profile updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to update user profile for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user profile: {str(e)}"
        )

@router.get("/recommendations")
async def get_profile_recommendations(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get personalized recommendations based on user profile"""
    try:
        recommendations = await user_profile_service.get_profile_recommendations(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
            "message": "Profile recommendations generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get profile recommendations for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.get("/completeness")
async def get_profile_completeness(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get profile completeness score and improvement suggestions"""
    try:
        profile = await user_profile_service.get_user_profile(user_id)
        recommendations = await user_profile_service.get_profile_recommendations(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "completeness_score": profile.get("profile_completeness", 0),
            "risk_score": profile.get("risk_score", 50),
            "is_new_profile": profile.get("is_new_profile", False),
            "improvement_suggestions": recommendations.get("profile_improvements", []),
            "timestamp": datetime.now().isoformat(),
            "message": "Profile completeness analysis completed"
        }
        
    except Exception as e:
        logger.error(f"Failed to get profile completeness for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze profile completeness: {str(e)}"
        )

@router.post("/validate")
async def validate_profile_data(
    profile_data: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Validate profile data before saving"""
    try:
        # Use the service's validation method
        validated_data = user_profile_service._validate_profile_updates(profile_data)
        
        # Calculate what the completeness would be
        current_profile = await user_profile_service.get_user_profile(user_id)
        test_profile = current_profile.copy()
        test_profile.update(validated_data)
        
        completeness = user_profile_service._calculate_profile_completeness(test_profile)
        risk_score = user_profile_service._calculate_risk_score(test_profile)
        
        return {
            "status": "success",
            "user_id": user_id,
            "validated_data": validated_data,
            "rejected_fields": [
                field for field in profile_data.keys() 
                if field not in validated_data
            ],
            "projected_completeness": completeness,
            "projected_risk_score": risk_score,
            "timestamp": datetime.now().isoformat(),
            "message": "Profile data validation completed"
        }
        
    except Exception as e:
        logger.error(f"Failed to validate profile data for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate profile data: {str(e)}"
        )

@router.get("/risk-assessment")
async def get_risk_assessment(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get detailed risk assessment based on user profile"""
    try:
        profile = await user_profile_service.get_user_profile(user_id)
        recommendations = await user_profile_service.get_profile_recommendations(user_id)
        
        risk_score = profile.get("risk_score", 50)
        
        # Determine risk category
        if risk_score <= 30:
            risk_category = "Conservative"
            risk_description = "Low risk tolerance with focus on capital preservation"
        elif risk_score <= 50:
            risk_category = "Moderate"
            risk_description = "Balanced approach between growth and stability"
        elif risk_score <= 70:
            risk_category = "Aggressive"
            risk_description = "Higher risk tolerance for potential higher returns"
        else:
            risk_category = "Very Aggressive"
            risk_description = "High risk tolerance with focus on maximum growth"
        
        return {
            "status": "success",
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_category": risk_category,
            "risk_description": risk_description,
            "risk_factors": {
                "risk_tolerance": profile.get("risk_tolerance", "medium"),
                "investment_timeline": profile.get("investment_timeline", "medium_term"),
                "max_position_size": profile.get("max_position_size", 15.0),
                "trading_frequency": profile.get("trading_frequency", "moderate")
            },
            "risk_management_recommendations": recommendations.get("risk_management", []),
            "timestamp": datetime.now().isoformat(),
            "message": "Risk assessment completed"
        }
        
    except Exception as e:
        logger.error(f"Failed to get risk assessment for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate risk assessment: {str(e)}"
        )

@router.get("/sector-preferences")
async def get_sector_preferences(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get sector allocation preferences and recommendations"""
    try:
        profile = await user_profile_service.get_user_profile(user_id)
        recommendations = await user_profile_service.get_profile_recommendations(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "preferred_sectors": profile.get("preferred_sectors", []),
            "sector_recommendations": recommendations.get("sector_allocation", []),
            "diversification_preference": profile.get("diversification_preference", "balanced"),
            "timestamp": datetime.now().isoformat(),
            "message": "Sector preferences retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get sector preferences for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sector preferences: {str(e)}"
        )

@router.post("/reset")
async def reset_user_profile(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Reset user profile to default values"""
    try:
        # Create default profile
        default_updates = user_profile_service.default_profile.copy()
        default_updates["updated_at"] = datetime.now().isoformat()
        
        # Update with defaults
        reset_profile = await user_profile_service.update_user_profile(
            user_id, default_updates
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "profile": reset_profile,
            "timestamp": datetime.now().isoformat(),
            "message": "User profile reset to default values"
        }
        
    except Exception as e:
        logger.error(f"Failed to reset user profile for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset user profile: {str(e)}"
        )

@router.get("/trading-strategy")
async def get_trading_strategy_recommendations(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get trading strategy recommendations based on profile"""
    try:
        recommendations = await user_profile_service.get_profile_recommendations(user_id)
        profile = await user_profile_service.get_user_profile(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "trading_strategy_recommendations": recommendations.get("trading_strategy", []),
            "portfolio_optimization": recommendations.get("portfolio_optimization", []),
            "current_settings": {
                "investment_timeline": profile.get("investment_timeline", "medium_term"),
                "trading_frequency": profile.get("trading_frequency", "moderate"),
                "auto_trading_enabled": profile.get("auto_trading_enabled", False),
                "stop_loss_preference": profile.get("stop_loss_preference"),
                "take_profit_preference": profile.get("take_profit_preference")
            },
            "timestamp": datetime.now().isoformat(),
            "message": "Trading strategy recommendations generated"
        }
        
    except Exception as e:
        logger.error(f"Failed to get trading strategy for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate trading strategy: {str(e)}"
        )