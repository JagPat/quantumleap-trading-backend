import logging
import json
from datetime import datetime
from .. import kite_service
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
            holdings = kite.holdings()
            positions = kite.positions()
            logger.info(f"Successfully fetched holdings and positions for user {user_id} from broker.")
        except Exception as e:
            logger.error(f"Error fetching portfolio from broker for user {user_id}: {e}")
            raise
            
        # 3. Create a snapshot
        timestamp = datetime.utcnow()
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            timestamp=timestamp,
            holdings=holdings,
            positions=positions
        )
        
        # 4. Store the snapshot in the database
        holdings_json = json.dumps(holdings)
        positions_json = json.dumps(positions['net']) # Storing net positions
        
        success = store_portfolio_snapshot(
            user_id=user_id,
            timestamp=timestamp.isoformat(),
            holdings=holdings_json,
            positions=positions_json
        )
        
        if not success:
            logger.error(f"Failed to store portfolio snapshot for user {user_id}")
            raise Exception("Failed to store portfolio snapshot in the database.")
            
        logger.info(f"Successfully created and stored portfolio snapshot for user {user_id}")
        return snapshot

    def get_latest_portfolio(self, user_id: str) -> PortfolioSnapshot | None:
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
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reconstructing portfolio snapshot for user {user_id}: {e}")
            return None

# Instantiate the service
portfolio_service = PortfolioService()
