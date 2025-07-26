import logging
import json
from datetime import datetime
from typing import Optional
from ..database.service import get_user_credentials, store_portfolio_snapshot, get_latest_portfolio_snapshot as get_snapshot_from_db
from .models import PortfolioSnapshot
from ..broker.kite_service import kite_service

logger = logging.getLogger(__name__)

class PortfolioService:
    def _calculate_portfolio_summary(self, holdings: list, positions: list) -> dict:
        """
        Calculate portfolio summary - ONLY aggregate broker-provided values
        Use broker calculations directly, only sum them up for totals
        """
        total_value = 0.0
        total_pnl = 0.0
        day_pnl = 0.0
        holdings_value = 0.0
        positions_value = 0.0
        
        # Aggregate holdings data (using broker-calculated values)
        for holding in holdings:
            if isinstance(holding, dict):
                # Current value = quantity * last_price (only for total calculation)
                quantity = holding.get('quantity', 0)
                last_price = holding.get('last_price', 0)
                if isinstance(quantity, (int, float)) and isinstance(last_price, (int, float)):
                    current_value = quantity * last_price
                    total_value += current_value
                    holdings_value += current_value
                
                # Use broker-calculated P&L directly (NO recalculation)
                broker_pnl = holding.get('pnl', 0)
                if isinstance(broker_pnl, (int, float)):
                    total_pnl += broker_pnl
                
                # Use broker-calculated day change directly (NO recalculation)
                broker_day_change = holding.get('day_change', 0)
                if isinstance(broker_day_change, (int, float)):
                    day_pnl += broker_day_change
        
        # Aggregate positions data (using broker-calculated values)
        for position in positions:
            if isinstance(position, dict):
                # Position value = quantity * last_price (only for total calculation)
                # Use net_quantity if available, otherwise use quantity
                quantity = position.get('net_quantity', position.get('quantity', 0))
                last_price = position.get('last_price', 0)
                if isinstance(quantity, (int, float)) and isinstance(last_price, (int, float)):
                    position_value = abs(quantity) * last_price
                    total_value += position_value
                    positions_value += position_value
                
                # Use broker-calculated unrealized P&L directly (NO recalculation)
                # Check multiple possible field names for unrealized P&L
                broker_unrealised = position.get('unrealised', position.get('pnl', 0))
                if isinstance(broker_unrealised, (int, float)):
                    total_pnl += broker_unrealised
                
                # Use broker-calculated M2M directly (NO recalculation)
                broker_m2m = position.get('m2m', 0)
                if isinstance(broker_m2m, (int, float)):
                    day_pnl += broker_m2m
        
        # Calculate total investment for percentage calculations
        total_investment = 0.0
        for holding in holdings:
            if isinstance(holding, dict):
                avg_price = holding.get('average_price', 0)
                quantity = holding.get('quantity', 0)
                if isinstance(avg_price, (int, float)) and isinstance(quantity, (int, float)):
                    total_investment += avg_price * quantity
        
        for position in positions:
            if isinstance(position, dict):
                avg_price = position.get('average_price', 0)
                quantity = position.get('quantity', 0)
                if isinstance(avg_price, (int, float)) and isinstance(quantity, (int, float)):
                    total_investment += avg_price * abs(quantity)
        
        # Calculate percentages
        total_pnl_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        day_pnl_percentage = (day_pnl / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'total_value': round(total_value, 2),
            'total_pnl': round(total_pnl, 2),
            'day_pnl': round(day_pnl, 2),
            'total_investment': round(total_investment, 2),
            'total_pnl_percentage': round(total_pnl_percentage, 2),
            'day_pnl_percentage': round(day_pnl_percentage, 2),
            'holdings_value': round(holdings_value, 2),
            'positions_value': round(positions_value, 2)
        }

    def _process_holdings_data(self, holdings: list) -> list:
        """
        Process holdings data - MINIMAL processing, use broker data directly
        Only add current_value for frontend convenience, everything else from broker
        """
        processed_holdings = []
        for holding in holdings:
            if isinstance(holding, dict):
                # ONLY calculate current_value for display convenience
                # Everything else comes directly from broker
                quantity = holding.get('quantity', 0)
                last_price = holding.get('last_price', 0)
                current_value = quantity * last_price if quantity and last_price else 0
                
                # Calculate P&L percentage for frontend convenience
                pnl_percentage = 0
                investment = quantity * holding.get('average_price', 0)
                if investment > 0:
                    pnl_percentage = (holding.get('pnl', 0) / investment) * 100
                
                # Use ALL broker data directly - no recalculation
                processed_holding = {
                    **holding,  # Keep ALL original broker fields unchanged
                    'current_value': round(current_value, 2),  # Only add this for frontend
                    'pnl_percentage': round(pnl_percentage, 2)  # Add percentage for frontend
                }
                processed_holdings.append(processed_holding)
        
        return processed_holdings

    def _process_positions_data(self, positions: list) -> list:
        """
        Process positions data - MINIMAL processing, use broker data directly
        Only add current_value for frontend convenience, everything else from broker
        """
        processed_positions = []
        for position in positions:
            if isinstance(position, dict):
                # ONLY calculate current_value for display convenience
                # Everything else comes directly from broker
                # Use net_quantity if available (for positions), otherwise use quantity
                quantity = position.get('net_quantity', position.get('quantity', 0))
                last_price = position.get('last_price', 0)
                current_value = abs(quantity) * last_price if quantity and last_price else 0
                
                # Calculate P&L percentage for frontend convenience
                pnl_percentage = 0
                investment = abs(quantity) * position.get('average_price', 0)
                if investment > 0:
                    unrealised_pnl = position.get('unrealised', position.get('pnl', 0))
                    pnl_percentage = (unrealised_pnl / investment) * 100
                
                # Use ALL broker data directly - no recalculation of P&L, M2M, etc.
                processed_position = {
                    **position,  # Keep ALL original broker fields unchanged
                    'current_value': round(current_value, 2),  # Only add this for frontend
                    'pnl_percentage': round(pnl_percentage, 2)  # Add percentage for frontend
                }
                processed_positions.append(processed_position)
        
        return processed_positions

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
            
        kite = kite_service.create_kite_client(credentials['api_key'], credentials['access_token'], credentials.get('api_secret', ''))
        
        # 2. Fetch holdings and positions from broker
        try:
            holdings = kite_service.get_holdings(kite)
            logger.info(f"Kite API holdings response for user {user_id}: {json.dumps(holdings)[:500]}")
            positions_dict = kite_service.get_positions(kite)
            logger.info(f"Kite API positions response for user {user_id}: {json.dumps(positions_dict)[:500]}")
            
            # Extract net positions (current day positions)
            net_positions = positions_dict.get('net', []) if isinstance(positions_dict, dict) else []
            
            # Validate structure
            if not isinstance(holdings, list):
                logger.error(f"Holdings is not a list for user {user_id}: {type(holdings)}")
                raise ValueError("Holdings data is not a list.")
            if not isinstance(net_positions, list):
                logger.error(f"Net positions is not a list for user {user_id}: {type(net_positions)}")
                raise ValueError("Positions data is not a list.")
            
            logger.info(f"Successfully fetched holdings ({len(holdings)} items) and positions ({len(net_positions)} items) for user {user_id} from broker.")
        except Exception as e:
            logger.error(f"Error fetching portfolio from broker for user {user_id}: {e}")
            raise Exception(f"Kite API error: {e}")
            
        # 3. Process and enrich the data
        processed_holdings = self._process_holdings_data(holdings)
        processed_positions = self._process_positions_data(net_positions)
        
        # 4. Calculate portfolio summary
        summary = self._calculate_portfolio_summary(holdings, net_positions)
        logger.info(f"Portfolio summary calculated for user {user_id}: {summary}")
        
        # 4. Create a snapshot
        timestamp = datetime.utcnow()
        timestamp_str = timestamp.isoformat()
        logger.info(f"Creating PortfolioSnapshot with timestamp: {timestamp_str} (type: {type(timestamp_str)})")
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            timestamp=timestamp_str,
            holdings=processed_holdings,  # Use processed data
            positions=processed_positions,  # Use processed data
            total_value=summary['total_value'],
            total_pnl=summary['total_pnl'],
            day_pnl=summary['day_pnl']
        )
        logger.info(f"PortfolioSnapshot created successfully with timestamp: {snapshot.timestamp} (type: {type(snapshot.timestamp)})")
        
        # 5. Store the snapshot in the database
        holdings_json = json.dumps(processed_holdings)  # Store processed data
        positions_json = json.dumps(processed_positions)  # Store processed data
        
        logger.info(f"Attempting to store portfolio snapshot for user {user_id}")
        logger.info(f"Timestamp: {timestamp.isoformat()}")
        logger.info(f"Holdings JSON length: {len(holdings_json)}")
        logger.info(f"Positions JSON length: {len(positions_json)}")
        
        try:
            success = store_portfolio_snapshot(
                user_id=user_id,
                timestamp=timestamp.isoformat(),
                holdings=holdings_json,
                positions=positions_json
            )
            logger.info(f"Database store operation completed. Success: {success}")
        except Exception as db_exc:
            logger.error(f"DB error storing portfolio snapshot for user {user_id}: {db_exc}")
            logger.error(f"DB error type: {type(db_exc).__name__}")
            logger.error(f"DB error details: {str(db_exc)}")
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
            # Handle both JSON strings and already parsed lists
            holdings_raw = snapshot_data['holdings']
            positions_raw = snapshot_data['positions']
            
            logger.info(f"Raw holdings type: {type(holdings_raw)}, value: {str(holdings_raw)[:100]}")
            logger.info(f"Raw positions type: {type(positions_raw)}, value: {str(positions_raw)[:100]}")
            
            # Parse holdings
            if isinstance(holdings_raw, str):
                holdings = json.loads(holdings_raw) if holdings_raw else []
            elif isinstance(holdings_raw, list):
                holdings = holdings_raw
            else:
                logger.error(f"Unexpected holdings type: {type(holdings_raw)}")
                holdings = []
            
            # Parse positions
            if isinstance(positions_raw, str):
                positions = json.loads(positions_raw) if positions_raw else []
            elif isinstance(positions_raw, list):
                positions = positions_raw
            else:
                logger.error(f"Unexpected positions type: {type(positions_raw)}")
                positions = []
            
            logger.info(f"Parsed holdings type: {type(holdings)}, length: {len(holdings)}")
            logger.info(f"Parsed positions type: {type(positions)}, length: {len(positions)}")
            
            # Calculate summary values
            summary = self._calculate_portfolio_summary(holdings, positions)
            
            # Reconstruct the PortfolioSnapshot object from stored data
            snapshot = PortfolioSnapshot(
                user_id=user_id,
                timestamp=snapshot_data['timestamp'],  # Keep as string from database
                holdings=holdings,
                positions=positions,
                total_value=summary['total_value'],
                total_pnl=summary['total_pnl'],
                day_pnl=summary['day_pnl']
            )
            logger.info(f"Successfully retrieved and reconstructed snapshot for user {user_id}")
            return snapshot
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Error reconstructing portfolio snapshot for user {user_id}: {e}")
            raise Exception(f"Error reconstructing portfolio snapshot: {e}")

# Instantiate the service
portfolio_service = PortfolioService()
