import logging
import json
from datetime import datetime
from typing import Optional
import kite_service
from ..database.service import get_user_credentials, store_portfolio_snapshot, get_latest_portfolio_snapshot as get_snapshot_from_db
from .models import PortfolioSnapshot

logger = logging.getLogger(__name__)

class PortfolioService:
    def fetch_and_store_portfolio(self, user_id: str) -> PortfolioSnapshot:
        """
        Fetches portfolio from broker, enriches it, and stores it in the database.
        """
        logger.info(f"Starting portfolio fetch for user_id: {user_id}")
        
        # 1. Get user credentials to initialize KiteConnect
        credentials = get_user_credentials(user_id)
        if not credentials:
            logger.error(f"No credentials found for user_id: {user_id}")
            raise ValueError("User credentials not found.")
            
        kite = kite_service.create_kite_client(credentials['api_key'], credentials['access_token'])
        
        # 2. Fetch holdings and positions from broker
        try:
            holdings = kite.get_holdings()
            logger.info(f"Kite API holdings response for user {user_id}: {json.dumps(holdings)[:500]}")
            positions_dict = kite.get_positions()
            logger.info(f"Kite API positions response for user {user_id}: {json.dumps(positions_dict)[:500]}")
            net_positions = positions_dict['net'] if isinstance(positions_dict, dict) and 'net' in positions_dict else []
            # Validate structure
            if not isinstance(holdings, list):
                logger.error(f"Holdings is not a list for user {user_id}: {type(holdings)}")
                raise ValueError("Holdings data is not a list.")
            if not isinstance(net_positions, list):
                logger.error(f"Net positions is not a list for user {user_id}: {type(net_positions)}")
                raise ValueError("Positions data is not a list.")
            logger.info(f"Successfully fetched holdings and positions for user {user_id} from broker.")
        except Exception as e:
            logger.error(f"Error fetching portfolio from broker for user {user_id}: {e}")
            raise Exception(f"Kite API error: {e}")
            
        # 3. Create a snapshot
        timestamp = datetime.utcnow()
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            timestamp=timestamp,
            holdings=holdings,
            positions=net_positions
        )
        
        # 4. Store the snapshot in the database
        holdings_json = json.dumps(holdings)
        positions_json = json.dumps(net_positions) # Store only net positions as a list
        
        try:
            success = store_portfolio_snapshot(
                user_id=user_id,
                timestamp=timestamp.isoformat(),
                holdings=holdings_json,
                positions=positions_json
            )
        except Exception as db_exc:
            logger.error(f"DB error storing portfolio snapshot for user {user_id}: {db_exc}")
            raise Exception(f"DB error: {db_exc}")
        
        if not success:
            logger.error(f"Failed to store portfolio snapshot for user {user_id}")
            raise Exception("Failed to store portfolio snapshot in the database.")
            
        logger.info(f"Successfully created and stored portfolio snapshot for user {user_id}")
        return snapshot

    def get_latest_portfolio(self, user_id: str) -> Optional[PortfolioSnapshot]:
        """
        Retrieves the latest stored portfolio snapshot for the user from the database.
        """
        logger.info(f"Retrieving latest portfolio snapshot for user_id: {user_id}")
        snapshot_data = get_snapshot_from_db(user_id)
        
        if not snapshot_data:
            logger.warning(f"No portfolio snapshot found for user {user_id}")
            return None
        
        try:
            # Reconstruct the PortfolioSnapshot object from stored data
            snapshot = PortfolioSnapshot(
                user_id=user_id,
                timestamp=datetime.fromisoformat(snapshot_data['timestamp']),
                holdings=json.loads(snapshot_data['holdings']),
                positions=json.loads(snapshot_data['positions'])
            )
            logger.info(f"Successfully retrieved and reconstructed snapshot for user {user_id}")
            return snapshot
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Error reconstructing portfolio snapshot for user {user_id}: {e}")
            raise Exception(f"Error reconstructing portfolio snapshot: {e}")

# Instantiate the service
portfolio_service = PortfolioService()
