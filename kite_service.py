import logging
import time
from typing import Dict, List, Any, Optional
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException, NetworkException, TokenException
from app.database.service import get_user_credentials
from datetime import datetime

logger = logging.getLogger(__name__)

class KiteService:
    """Service class for handling Kite Connect API operations with robust retry logic"""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        if access_token:
            self.kite.set_access_token(access_token)
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1.0  # Start with 1 second
        self.max_delay = 8.0   # Cap at 8 seconds
    
    def _make_request_with_retry(self, func, *args, **kwargs):
        """Make API request with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Making request attempt {attempt + 1}/{self.max_retries + 1}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Request succeeded on attempt {attempt + 1}")
                
                return result
                
            except NetworkException as e:
                last_exception = e
                logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                    
            except TokenException as e:
                # Token errors are not retryable
                logger.error(f"Token error: {str(e)}")
                raise
                
            except KiteException as e:
                last_exception = e
                error_message = str(e).lower()
                
                # Check for rate limiting
                if 'rate limit' in error_message or 'too many requests' in error_message:
                    logger.warning(f"Rate limit hit on attempt {attempt + 1}: {str(e)}")
                    
                    if attempt < self.max_retries:
                        # Longer delay for rate limiting
                        delay = min(self.base_delay * (3 ** attempt), self.max_delay)
                        logger.info(f"Rate limit retry in {delay} seconds...")
                        time.sleep(delay)
                        continue
                
                # Other Kite errors are generally not retryable
                logger.error(f"Kite API error: {str(e)}")
                raise
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                    
        # If we get here, all retries failed
        logger.error(f"All {self.max_retries + 1} attempts failed")
        raise last_exception
    
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """Generate session using request token"""
        try:
            data = self._make_request_with_retry(
                self.kite.generate_session, 
                request_token, 
                api_secret=self.api_secret
            )
            self.kite.set_access_token(data["access_token"])
            return data
        except Exception as e:
            logger.error(f"Error during session generation: {str(e)}")
            raise
    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            return self._make_request_with_retry(self.kite.profile)
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            raise
    
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get user holdings with enhanced data fields"""
        try:
            raw_holdings = self._make_request_with_retry(self.kite.holdings)
            
            # Enhance holdings data with calculated fields
            enhanced_holdings = []
            fetch_timestamp = datetime.now().timestamp()
            
            for holding in raw_holdings:
                quantity = holding.get("quantity", 0)
                average_price = holding.get("average_price", 0)
                last_price = holding.get("last_price", 0)
                
                # Calculate enhanced fields
                invested_amount = average_price * quantity
                current_value = last_price * quantity
                pnl = holding.get("pnl", 0)
                pnl_percentage = (pnl / invested_amount * 100) if invested_amount > 0 else 0
                
                enhanced_holding = {
                    **holding,  # Keep all original fields
                    "invested_amount": round(invested_amount, 2),
                    "current_value": round(current_value, 2),
                    "pnl_percentage": round(pnl_percentage, 2),
                    "fetch_timestamp": fetch_timestamp
                }
                enhanced_holdings.append(enhanced_holding)
            
            logger.info(f"Successfully fetched {len(enhanced_holdings)} holdings with enhanced data")
            return enhanced_holdings
            
        except Exception as e:
            logger.error(f"Error getting holdings: {str(e)}")
            raise
    
    def get_positions(self) -> Dict[str, Any]:
        """Get user positions with enhanced data fields"""
        try:
            raw_positions = self._make_request_with_retry(self.kite.positions)
            
            # Enhance positions data
            fetch_timestamp = datetime.now().timestamp()
            
            # Enhance net positions
            if "net" in raw_positions and isinstance(raw_positions["net"], list):
                enhanced_net = []
                for position in raw_positions["net"]:
                    quantity = position.get("quantity", 0)
                    average_price = position.get("average_price", 0)
                    last_price = position.get("last_price", 0)
                    
                    # Calculate enhanced fields
                    invested_amount = abs(average_price * quantity)
                    current_value = abs(last_price * quantity)
                    pnl = position.get("pnl", 0)
                    pnl_percentage = (pnl / invested_amount * 100) if invested_amount > 0 else 0
                    
                    enhanced_position = {
                        **position,  # Keep all original fields
                        "invested_amount": round(invested_amount, 2),
                        "current_value": round(current_value, 2),
                        "pnl_percentage": round(pnl_percentage, 2),
                        "fetch_timestamp": fetch_timestamp
                    }
                    enhanced_net.append(enhanced_position)
                
                raw_positions["net"] = enhanced_net
            
            # Enhance day positions similarly
            if "day" in raw_positions and isinstance(raw_positions["day"], list):
                enhanced_day = []
                for position in raw_positions["day"]:
                    quantity = position.get("quantity", 0)
                    average_price = position.get("average_price", 0)
                    last_price = position.get("last_price", 0)
                    
                    # Calculate enhanced fields
                    invested_amount = abs(average_price * quantity)
                    current_value = abs(last_price * quantity)
                    pnl = position.get("pnl", 0)
                    pnl_percentage = (pnl / invested_amount * 100) if invested_amount > 0 else 0
                    
                    enhanced_position = {
                        **position,  # Keep all original fields
                        "invested_amount": round(invested_amount, 2),
                        "current_value": round(current_value, 2),
                        "pnl_percentage": round(pnl_percentage, 2),
                        "fetch_timestamp": fetch_timestamp
                    }
                    enhanced_day.append(enhanced_position)
                
                raw_positions["day"] = enhanced_day
            
            logger.info(f"Successfully fetched positions with enhanced data")
            return raw_positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            raise
    
    def get_margins(self) -> Dict[str, Any]:
        """Get user margins"""
        try:
            return self._make_request_with_retry(self.kite.margins)
        except Exception as e:
            logger.error(f"Error getting margins: {str(e)}")
            raise

def get_kite_service(user_id: str) -> Optional[KiteService]:
    """Get KiteService instance for a user"""
    try:
        user_creds = get_user_credentials(user_id)
        if not user_creds:
            logger.error(f"No credentials found for user: {user_id}")
            return None
        
        if not user_creds.get("access_token"):
            logger.error(f"No access token found for user: {user_id}")
            return None
        
        return KiteService(
            api_key=user_creds["api_key"],
            api_secret=user_creds["api_secret"],
            access_token=user_creds["access_token"]
        )
    except Exception as e:
        logger.error(f"Error creating KiteService for user {user_id}: {str(e)}")
        return None

def calculate_portfolio_summary(holdings: List[Dict[str, Any]], positions: Dict[str, Any]) -> Dict[str, float]:
    """Calculate enhanced portfolio summary from holdings and positions"""
    try:
        total_value = 0.0
        total_pnl = 0.0
        todays_pnl = 0.0
        total_invested = 0.0
        
        # Calculate from enhanced holdings
        for holding in holdings:
            # Use enhanced fields if available, fallback to calculated values
            if "current_value" in holding:
                total_value += holding["current_value"]
            else:
                quantity = holding.get("quantity", 0)
                last_price = holding.get("last_price", 0)
                total_value += quantity * last_price
            
            if "invested_amount" in holding:
                total_invested += holding["invested_amount"]
            else:
                quantity = holding.get("quantity", 0)
                average_price = holding.get("average_price", 0)
                total_invested += quantity * average_price
            
            total_pnl += holding.get("pnl", 0)
        
        # Calculate from enhanced positions (day's P&L)
        net_positions = positions.get("net", [])
        for position in net_positions:
            todays_pnl += position.get("pnl", 0)
            
            # Add position values to totals
            if "current_value" in position:
                total_value += position["current_value"]
            
            if "invested_amount" in position:
                total_invested += position["invested_amount"]
        
        # Calculate overall P&L percentage
        total_pnl_percentage = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "todays_pnl": round(todays_pnl, 2),
            "total_invested": round(total_invested, 2),
            "total_pnl_percentage": round(total_pnl_percentage, 2),
            "fetch_timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        logger.error(f"Error calculating portfolio summary: {str(e)}")
        return {
            "total_value": 0.0,
            "total_pnl": 0.0,
            "todays_pnl": 0.0,
            "total_invested": 0.0,
            "total_pnl_percentage": 0.0,
            "fetch_timestamp": datetime.now().timestamp()
        }

def format_holdings_data(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format enhanced holdings data for API response"""
    try:
        formatted_holdings = []
        for holding in holdings:
            formatted_holding = {
                "symbol": holding.get("tradingsymbol", ""),
                "quantity": holding.get("quantity", 0),
                "avg_price": holding.get("average_price", 0),
                "current_price": holding.get("last_price", 0),
                "pnl": holding.get("pnl", 0),
                # Enhanced fields
                "invested_amount": holding.get("invested_amount", 0),
                "current_value": holding.get("current_value", 0),
                "pnl_percentage": holding.get("pnl_percentage", 0),
                "fetch_timestamp": holding.get("fetch_timestamp", 0)
            }
            formatted_holdings.append(formatted_holding)
        return formatted_holdings
    except Exception as e:
        logger.error(f"Error formatting holdings data: {str(e)}")
        return [] 