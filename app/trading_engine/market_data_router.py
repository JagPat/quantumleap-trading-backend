"""
Market Data Router
Provides API endpoints for market data management and processing
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Query
from pydantic import BaseModel
from datetime import datetime

from app.trading_engine.market_data_manager import get_market_data_manager
from app.trading_engine.market_data_processor import get_market_data_processor
from app.trading_engine.models import PriceData

logger = logging.getLogger(__name__)
router = APIRouter()

class PriceDataRequest(BaseModel):
    symbol: str
    price: float
    bid: float = 0.0
    ask: float = 0.0
    volume: int = 0
    change: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0

class SubscriptionRequest(BaseModel):
    symbol: str
    subscriber_id: str

@router.get("/status")
async def get_market_data_status(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get market data system status"""
    try:
        manager = get_market_data_manager()
        processor = get_market_data_processor()
        
        if not manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
        
        # Get manager status
        manager_status = await manager.get_market_status()
        
        # Get processor metrics if available
        processor_metrics = {}
        if processor:
            processor_metrics = processor.get_metrics()
        
        return {
            "status": "success",
            "market_data_manager": manager_status,
            "market_data_processor": processor_metrics,
            "user_id": x_user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting market data status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe")
async def subscribe_to_symbol(
    request: SubscriptionRequest,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Subscribe to real-time price updates for a symbol"""
    try:
        manager = get_market_data_manager()
        if not manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
        
        # Create a callback function (in production, this would be more sophisticated)
        def price_callback(price_update):
            logger.info(f"Price update for {request.symbol}: ${price_update.price}")
        
        success = await manager.subscribe_to_symbol(
            request.symbol, 
            f"{x_user_id}_{request.subscriber_id}", 
            price_callback
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Subscribed to {request.symbol}",
                "symbol": request.symbol,
                "subscriber_id": request.subscriber_id,
                "user_id": x_user_id
            }
        else:
            raise HTTPException(status_code=400, detail="Subscription failed")
        
    except Exception as e:
        logger.error(f"Error subscribing to symbol: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price/{symbol}")
async def get_current_price(
    symbol: str,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get current price for a symbol"""
    try:
        manager = get_market_data_manager()
        if not manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
        
        price_data = await manager.get_current_price(symbol)
        
        if price_data:
            return {
                "status": "success",
                "symbol": symbol,
                "price_data": price_data.to_dict(),
                "user_id": x_user_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"No price data available for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting current price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/price")
async def submit_price_data(
    request: PriceDataRequest,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Submit price data for processing"""
    try:
        processor = get_market_data_processor()
        if not processor:
            raise HTTPException(status_code=503, detail="Market data processor not available")
        
        # Convert request to PriceData
        price_data = PriceData(
            symbol=request.symbol,
            price=request.price,
            bid=request.bid or request.price - 0.01,
            ask=request.ask or request.price + 0.01,
            volume=request.volume,
            timestamp=datetime.utcnow(),
            change=request.change,
            change_percent=request.change_percent,
            high=request.high or request.price,
            low=request.low or request.price,
            open_price=request.open_price or request.price
        )
        
        # Process the data
        processed_result = await processor.process_price_data(price_data)
        
        return {
            "status": "success",
            "message": "Price data processed",
            "processed_data": processed_result.to_dict(),
            "user_id": x_user_id
        }
        
    except Exception as e:
        logger.error(f"Error processing price data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing/metrics")
async def get_processing_metrics(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get market data processing metrics"""
    try:
        processor = get_market_data_processor()
        if not processor:
            raise HTTPException(status_code=503, detail="Market data processor not available")
        
        metrics = processor.get_metrics()
        
        return {
            "status": "success",
            "metrics": {
                "total_updates": metrics.total_updates,
                "valid_updates": metrics.valid_updates,
                "invalid_updates": metrics.invalid_updates,
                "average_latency_ms": metrics.average_latency_ms,
                "max_latency_ms": metrics.max_latency_ms,
                "updates_per_second": metrics.updates_per_second,
                "last_reset": metrics.last_reset.isoformat()
            },
            "user_id": x_user_id
        }
        
    except Exception as e:
        logger.error(f"Error getting processing metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    hours: int = Query(default=24, description="Hours of historical data to retrieve"),
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get historical price data for a symbol"""
    try:
        processor = get_market_data_processor()
        if not processor:
            raise HTTPException(status_code=503, detail="Market data processor not available")
        
        historical_data = await processor.get_historical_data(symbol, hours=hours)
        
        return {
            "status": "success",
            "symbol": symbol,
            "hours": hours,
            "data_points": len(historical_data),
            "historical_data": [data.to_dict() for data in historical_data],
            "user_id": x_user_id
        }
        
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/price-update")
async def test_price_update(
    background_tasks: BackgroundTasks,
    symbol: str = Query(default="TESTSTOCK", description="Symbol to test"),
    count: int = Query(default=10, description="Number of test updates"),
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Generate test price updates for testing"""
    try:
        processor = get_market_data_processor()
        if not processor:
            raise HTTPException(status_code=503, detail="Market data processor not available")
        
        async def generate_test_updates():
            """Generate test price updates"""
            import random
            base_price = 100.0
            
            for i in range(count):
                # Generate random price movement
                change_pct = random.uniform(-0.02, 0.02)  # ±2%
                new_price = base_price * (1 + change_pct)
                
                test_data = PriceData(
                    symbol=symbol,
                    price=round(new_price, 2),
                    bid=round(new_price - 0.01, 2),
                    ask=round(new_price + 0.01, 2),
                    volume=random.randint(1000, 10000),
                    timestamp=datetime.utcnow(),
                    change=round(new_price - base_price, 2),
                    change_percent=round(change_pct * 100, 2)
                )
                
                await processor.process_price_data(test_data)
                base_price = new_price
                
                # Small delay between updates
                await asyncio.sleep(0.1)
        
        # Run test updates in background
        background_tasks.add_task(generate_test_updates)
        
        return {
            "status": "success",
            "message": f"Generating {count} test price updates for {symbol}",
            "symbol": symbol,
            "count": count,
            "user_id": x_user_id
        }
        
    except Exception as e:
        logger.error(f"Error generating test price updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))