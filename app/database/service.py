# ... existing code ...
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                holdings TEXT NOT NULL,
                positions TEXT NOT NULL,
                summary TEXT NOT NULL,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        conn.commit()
    except Exception as e:
# ... existing code ...
def save_portfolio_snapshot(user_id: str, holdings: str, positions: str, summary: str):
    """Saves a new portfolio snapshot for the user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO portfolio_snapshots (user_id, holdings, positions, summary) VALUES (?, ?, ?, ?)",
            (user_id, holdings, positions, summary),
        )
        conn.commit()
        logger.info(f"Successfully saved portfolio snapshot for user: {user_id}")
    except Exception as e:
        logger.error(f"Error saving portfolio snapshot for user {user_id}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_latest_portfolio_snapshot(user_id: str):
    """Retrieves the most recent portfolio snapshot for the user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, holdings, positions, summary, imported_at FROM portfolio_snapshots WHERE user_id = ? ORDER BY imported_at DESC LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "holdings": row[1],
                "positions": row[2],
                "summary": row[3],
                "imported_at": row[4],
            }
        return None
    except Exception as e:
        logger.error(f"Error getting latest portfolio snapshot for user {user_id}: {e}")
        raise
    finally:
        conn.close()
