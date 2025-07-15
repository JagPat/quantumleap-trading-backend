import json
from kiteconnect import KiteException
from ..kite_service import get_kite_service, calculate_portfolio_summary, format_holdings_data
from ..database.service import save_portfolio_snapshot, get_latest_portfolio_snapshot
from ..logger import logger

class PortfolioService:
    def fetch_and_store_portfolio(self, user_id: str):
        """
        Fetches portfolio from broker, enriches it, and stores it in the database.
        """
        try:
            kite_service = get_kite_service(user_id)
            if not kite_service:
                raise Exception("Kite service not available for user.")

            holdings = kite_service.get_holdings()
            positions = kite_service.get_positions()
            
            summary = calculate_portfolio_summary(holdings, positions)
            
            save_portfolio_snapshot(
                user_id=user_id,
                holdings=json.dumps(format_holdings_data(holdings)),
                positions=json.dumps(positions),
                summary=json.dumps(summary),
            )
            
            logger.info(f"Successfully fetched and stored portfolio for user {user_id}")
            return get_latest_portfolio_snapshot(user_id)
            
        except KiteException as e:
            logger.error(f"Kite API error fetching portfolio for {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching portfolio for {user_id}: {e}")
            raise

portfolio_service = PortfolioService() 