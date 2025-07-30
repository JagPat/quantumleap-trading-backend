"""
Market Condition Router
Provides API endpoints for market condition monitoring
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from datetime import datetime

from app.trading_engine.market_condition_monitor import get_market_condition_monitor

logger = logging.getLogger(__name__)
router = APIRouter()

class MarketHoursRequest(BaseModel):
    pre_market_start: str = "04:00"
    market_open: str = "09:30"
    market_close: str = "16:00"
    after_hours_end: str = "20:00"
    timezone: str = "US/Eastern"

@router.get("/status")
async def get_market_condition_status(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get market condition monitoring status"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        summary = monitor.get_condition_summary()
        
        return {
            "status": "success",
            "market_condition_summary": summary,
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting market condition status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/condition/{symbol}")
async def get_symbol_condition(
    symbol: str,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get current market condition for a specific symbol"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        condition_data = monitor.get_current_condition(symbol)
        
        if condition_data:
            return {
                "status": "success",
                "symbol": symbol,
                "condition": {
                    "condition": condition_data.condition.value,
                    "volatility_level": condition_data.volatility_level.value,
                    "volatility_score": condition_data.volatility_score,
                    "price_change_percent": condition_data.price_change_percent,
                    "volume_ratio": condition_data.volume_ratio,
                    "gap_percent": condition_data.gap_percent,
                    "trend_strength": condition_data.trend_strength,
                    "support_level": condition_data.support_level,
                    "resistance_level": condition_data.resistance_level,
                    "confidence": condition_data.confidence,
                    "timestamp": condition_data.timestamp.isoformat()
                },
                "user_id": x_user_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"No condition data available for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting symbol condition: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session")
async def get_market_session(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get current market session information"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        session = monitor.get_market_session()
        is_open = monitor.is_market_open()
        is_trading_hours = monitor.is_trading_hours()
        global_condition = monitor.get_global_condition()
        
        return {
            "status": "success",
            "market_session": {
                "current_session": session.value,
                "is_market_open": is_open,
                "is_trading_hours": is_trading_hours,
                "global_condition": global_condition.value
            },
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting market session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/volatility/{symbol}")
async def get_symbol_volatility(
    symbol: str,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get volatility analysis for a specific symbol"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        condition_data = monitor.get_current_condition(symbol)
        
        if condition_data:
            return {
                "status": "success",
                "symbol": symbol,
                "volatility": {
                    "level": condition_data.volatility_level.value,
                    "score": condition_data.volatility_score,
                    "confidence": condition_data.confidence,
                    "timestamp": condition_data.timestamp.isoformat()
                },
                "user_id": x_user_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"No volatility data available for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting symbol volatility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading-halt")
async def get_trading_halt_status(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get trading halt status for all symbols"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        summary = monitor.get_condition_summary()
        halted_symbols = summary.get("trading_halted_symbols", [])
        
        # Get detailed halt reasons
        halt_details = []
        for symbol in halted_symbols:
            condition_data = monitor.get_current_condition(symbol)
            if condition_data:
                halt_details.append({
                    "symbol": symbol,
                    "condition": condition_data.condition.value,
                    "volatility_level": condition_data.volatility_level.value,
                    "price_change_percent": condition_data.price_change_percent,
                    "timestamp": condition_data.timestamp.isoformat()
                })
        
        return {
            "status": "success",
            "trading_halt_status": {
                "total_halted": len(halted_symbols),
                "halted_symbols": halted_symbols,
                "halt_details": halt_details
            },
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trading halt status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading-halt/{symbol}")
async def check_symbol_trading_halt(
    symbol: str,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Check if trading should be halted for a specific symbol"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        should_halt = monitor.should_halt_trading(symbol)
        condition_data = monitor.get_current_condition(symbol)
        
        result = {
            "status": "success",
            "symbol": symbol,
            "should_halt_trading": should_halt,
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if condition_data:
            result["condition_details"] = {
                "condition": condition_data.condition.value,
                "volatility_level": condition_data.volatility_level.value,
                "price_change_percent": condition_data.price_change_percent,
                "confidence": condition_data.confidence
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking trading halt for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def get_market_trends(
    min_trend_strength: float = Query(default=0.5, description="Minimum trend strength to include"),
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get trending symbols and their trend analysis"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        summary = monitor.get_condition_summary()
        trending_symbols = []
        
        # Get all current conditions
        for symbol in summary.get("conditions_by_type", {}):
            condition_data = monitor.get_current_condition(symbol)
            if condition_data and abs(condition_data.trend_strength) >= min_trend_strength:
                trending_symbols.append({
                    "symbol": symbol,
                    "condition": condition_data.condition.value,
                    "trend_strength": condition_data.trend_strength,
                    "price_change_percent": condition_data.price_change_percent,
                    "support_level": condition_data.support_level,
                    "resistance_level": condition_data.resistance_level,
                    "confidence": condition_data.confidence,
                    "timestamp": condition_data.timestamp.isoformat()
                })
        
        # Sort by trend strength
        trending_symbols.sort(key=lambda x: abs(x["trend_strength"]), reverse=True)
        
        return {
            "status": "success",
            "trending_analysis": {
                "total_trending": len(trending_symbols),
                "min_trend_strength": min_trend_strength,
                "trending_symbols": trending_symbols
            },
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting market trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gaps")
async def get_price_gaps(
    min_gap_percent: float = Query(default=2.0, description="Minimum gap percentage to include"),
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get symbols with significant price gaps"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        summary = monitor.get_condition_summary()
        gap_symbols = []
        
        # Get all current conditions
        for symbol in summary.get("conditions_by_type", {}):
            condition_data = monitor.get_current_condition(symbol)
            if condition_data and abs(condition_data.gap_percent) >= min_gap_percent:
                gap_symbols.append({
                    "symbol": symbol,
                    "condition": condition_data.condition.value,
                    "gap_percent": condition_data.gap_percent,
                    "price_change_percent": condition_data.price_change_percent,
                    "volume_ratio": condition_data.volume_ratio,
                    "confidence": condition_data.confidence,
                    "timestamp": condition_data.timestamp.isoformat()
                })
        
        # Sort by gap size
        gap_symbols.sort(key=lambda x: abs(x["gap_percent"]), reverse=True)
        
        return {
            "status": "success",
            "gap_analysis": {
                "total_gaps": len(gap_symbols),
                "min_gap_percent": min_gap_percent,
                "gap_symbols": gap_symbols
            },
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting price gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/high-volatility")
async def get_high_volatility_symbols(
    min_volatility_level: str = Query(default="high", description="Minimum volatility level (normal, high, very_high, extreme)"),
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get symbols with high volatility"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        # Define volatility level hierarchy
        volatility_hierarchy = {
            "very_low": 0,
            "low": 1,
            "normal": 2,
            "high": 3,
            "very_high": 4,
            "extreme": 5
        }
        
        min_level = volatility_hierarchy.get(min_volatility_level, 3)
        
        summary = monitor.get_condition_summary()
        volatile_symbols = []
        
        # Get all current conditions
        for symbol in summary.get("conditions_by_type", {}):
            condition_data = monitor.get_current_condition(symbol)
            if condition_data:
                symbol_level = volatility_hierarchy.get(condition_data.volatility_level.value, 0)
                if symbol_level >= min_level:
                    volatile_symbols.append({
                        "symbol": symbol,
                        "condition": condition_data.condition.value,
                        "volatility_level": condition_data.volatility_level.value,
                        "volatility_score": condition_data.volatility_score,
                        "price_change_percent": condition_data.price_change_percent,
                        "volume_ratio": condition_data.volume_ratio,
                        "confidence": condition_data.confidence,
                        "timestamp": condition_data.timestamp.isoformat()
                    })
        
        # Sort by volatility score
        volatile_symbols.sort(key=lambda x: x["volatility_score"], reverse=True)
        
        return {
            "status": "success",
            "volatility_analysis": {
                "total_volatile": len(volatile_symbols),
                "min_volatility_level": min_volatility_level,
                "volatile_symbols": volatile_symbols
            },
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting high volatility symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_comprehensive_summary(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get comprehensive market condition summary"""
    try:
        monitor = get_market_condition_monitor()
        if not monitor:
            raise HTTPException(status_code=503, detail="Market condition monitor not available")
        
        summary = monitor.get_condition_summary()
        session = monitor.get_market_session()
        is_open = monitor.is_market_open()
        is_trading_hours = monitor.is_trading_hours()
        global_condition = monitor.get_global_condition()
        
        return {
            "status": "success",
            "comprehensive_summary": {
                "market_session": {
                    "current_session": session.value,
                    "is_market_open": is_open,
                    "is_trading_hours": is_trading_hours
                },
                "global_condition": global_condition.value,
                "monitoring_stats": {
                    "symbols_monitored": summary["symbols_monitored"],
                    "conditions_by_type": summary["conditions_by_type"],
                    "volatility_distribution": summary["volatility_distribution"],
                    "trading_halted_symbols": summary["trading_halted_symbols"]
                }
            },
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))