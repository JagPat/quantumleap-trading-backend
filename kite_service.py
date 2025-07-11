import logging
from typing import Dict, List, Any, Optional
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException
from app.database.service import get_user_credentials

logger = logging.getLogger(__name__)

class KiteService:
    """Service class for handling Kite Connect API operations"""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        if access_token:
            self.kite.set_access_token(access_token)
    
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """Generate session using request token"""
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.kite.set_access_token(data["access_token"])
            return data
        except KiteException as e:
            logger.error(f"Kite API error during session generation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during session generation: {str(e)}")
            raise
    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            return self.kite.profile()
        except KiteException as e:
            logger.error(f"Kite API error getting profile: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting profile: {str(e)}")
            raise
    
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get user holdings"""
        try:
            return self.kite.holdings()
        except KiteException as e:
            logger.error(f"Kite API error getting holdings: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting holdings: {str(e)}")
            raise
    
    def get_positions(self) -> Dict[str, Any]:
        """Get user positions"""
        try:
            return self.kite.positions()
        except KiteException as e:
            logger.error(f"Kite API error getting positions: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting positions: {str(e)}")
            raise
    
    def get_margins(self) -> Dict[str, Any]:
        """Get user margins"""
        try:
            return self.kite.margins()
        except KiteException as e:
            logger.error(f"Kite API error getting margins: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting margins: {str(e)}")
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
    """Calculate portfolio summary from holdings and positions"""
    try:
        total_value = 0.0
        total_pnl = 0.0
        todays_pnl = 0.0
        
        # Calculate from holdings
        for holding in holdings:
            quantity = holding.get("quantity", 0)
            last_price = holding.get("last_price", 0)
            average_price = holding.get("average_price", 0)
            
            current_value = quantity * last_price
            total_value += current_value
            
            pnl = (last_price - average_price) * quantity
            total_pnl += pnl
        
        # Calculate from positions (day's P&L)
        net_positions = positions.get("net", [])
        for position in net_positions:
            todays_pnl += position.get("pnl", 0)
        
        return {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "todays_pnl": round(todays_pnl, 2)
        }
    except Exception as e:
        logger.error(f"Error calculating portfolio summary: {str(e)}")
        return {
            "total_value": 0.0,
            "total_pnl": 0.0,
            "todays_pnl": 0.0
        }

def format_holdings_data(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format holdings data for API response"""
    try:
        formatted_holdings = []
        for holding in holdings:
            formatted_holding = {
                "symbol": holding.get("tradingsymbol", ""),
                "quantity": holding.get("quantity", 0),
                "avg_price": holding.get("average_price", 0),
                "current_price": holding.get("last_price", 0),
                "pnl": holding.get("pnl", 0)
            }
            formatted_holdings.append(formatted_holding)
        return formatted_holdings
    except Exception as e:
        logger.error(f"Error formatting holdings data: {str(e)}")
        return [] 