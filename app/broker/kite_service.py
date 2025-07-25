"""
Kite Connect Service
Handles Kite Connect API integration for portfolio and trading operations
"""
import logging
from typing import Dict, List, Optional
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)

class KiteService:
    """Service for Kite Connect API operations"""
    
    def create_kite_client(self, api_key: str, access_token: str, api_secret: str = '') -> KiteConnect:
        """
        Create and configure a Kite Connect client
        
        Args:
            api_key: Kite Connect API key
            access_token: User's access token
            api_secret: API secret (optional for most operations)
            
        Returns:
            Configured KiteConnect instance
        """
        try:
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            
            logger.info(f"Created Kite client for API key: {api_key[:8]}...")
            return kite
            
        except Exception as e:
            logger.error(f"Failed to create Kite client: {e}")
            raise Exception(f"Kite client creation failed: {e}")
    
    def get_holdings(self, kite: KiteConnect) -> List[Dict]:
        """
        Fetch holdings from Kite Connect
        
        Args:
            kite: Configured KiteConnect instance
            
        Returns:
            List of holdings
        """
        try:
            holdings = kite.holdings()
            logger.info(f"Fetched {len(holdings)} holdings from Kite Connect")
            return holdings
            
        except Exception as e:
            logger.error(f"Failed to fetch holdings: {e}")
            raise Exception(f"Holdings fetch failed: {e}")
    
    def get_positions(self, kite: KiteConnect) -> Dict:
        """
        Fetch positions from Kite Connect
        
        Args:
            kite: Configured KiteConnect instance
            
        Returns:
            Dictionary containing day and net positions
        """
        try:
            positions = kite.positions()
            logger.info(f"Fetched positions from Kite Connect: {len(positions.get('net', []))} net positions")
            return positions
            
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise Exception(f"Positions fetch failed: {e}")
    
    def get_profile(self, kite: KiteConnect) -> Dict:
        """
        Fetch user profile from Kite Connect
        
        Args:
            kite: Configured KiteConnect instance
            
        Returns:
            User profile data
        """
        try:
            profile = kite.profile()
            logger.info(f"Fetched profile for user: {profile.get('user_id', 'unknown')}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to fetch profile: {e}")
            raise Exception(f"Profile fetch failed: {e}")

# Create singleton instance
kite_service = KiteService()