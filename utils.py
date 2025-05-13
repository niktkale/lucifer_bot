from typing import Tuple, Optional
from datetime import datetime, timedelta
import sqlite3
from config import Config
from database import Database

db = Database()


async def is_admin(user_id: int) -> bool:
    user = db.get_user(user_id)
    return (user and user['is_admin']) or (user_id in Config.ADMIN_IDS)


async def register_user(user_id: int, username: str = None):
    db.execute(
        """INSERT OR IGNORE INTO users (user_id, username, is_admin) 
        VALUES (?, ?, ?)""",
        (user_id, username, user_id in Config.ADMIN_IDS)
    )
    db.commit()


async def can_get_daily(user_id: int) -> Tuple[bool, Optional[str]]:
    user = db.get_user(user_id)
    if not user or not user['last_daily']:
        return True, None

    last_time = datetime.fromisoformat(user['last_daily'])
    if datetime.now() - last_time < timedelta(hours=Config.DAILY_COOLDOWN):
        next_time = (last_time + timedelta(hours=Config.DAILY_COOLDOWN)).strftime("%H:%M")
        return False, next_time
    return True, None


async def transfer_money(from_user: int, to_user: int, amount: int) -> bool:
    if from_user == to_user:
        return False

    try:
        with db.conn:
            sender = db.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (from_user,)
            ).fetchone()

            if not sender or sender['balance'] < amount:
                return False

            db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, from_user)
            )
            db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, to_user)
            )

            db.add_transaction(
                from_user, to_user, amount,
                f"Transfer from {from_user} to {to_user}"
            )
        return True
    except sqlite3.Error:
        return False


async def get_stats():
    return db.execute("""
        SELECT 
            COUNT(*) as total_users,
            SUM(balance) as total_balance,
            (SELECT COUNT(*) FROM transactions) as total_transactions
        FROM users
    """).fetchone()


async def add_money_to_user(user_id: int, amount: int):
    db.update_balance(user_id, amount)
    db.add_transaction(0, user_id, amount, "Admin deposit")


