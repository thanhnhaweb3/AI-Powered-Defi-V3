from database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CreditService:
    def __init__(self):
        self.db = Database("credits.db")

    def check_credits(self, user_id: str) -> int:
        result = self.db.fetch_one("SELECT credits FROM credits WHERE user_id = ?", (user_id,))
        return result[0] if result else 0

    def deduct_credits(self, user_id: str, model: str) -> bool:
        cost = {"openai": 1, "anthropic": 2, "deepseek": 1}.get(model, 1)
        credits = self.check_credits(user_id)
        if credits < cost:
            return False
        self.db.execute("INSERT OR REPLACE INTO credits (user_id, credits) VALUES (?, ?)", (user_id, credits - cost))
        logger.info(f"Deducted {cost} credits from {user_id} for model {model}")
        return True

    def add_credits(self, user_id: str, amount: int):
        current_credits = self.check_credits(user_id)
        self.db.execute("INSERT OR REPLACE INTO credits (user_id, credits) VALUES (?, ?)", (user_id, current_credits + amount))
        logger.info(f"Added {amount} credits to {user_id}")
