import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class Config:
    TOKEN = "7659091957:AAFq5YgTGdUrmNlHg4BGIfrbWL6heVnevAw"
    DB_NAME = "lucifer_bot.db"
    ADMIN_IDS = {6535180095}
    DAILY_COOLDOWN = 24  # Часы между начислениями
    MIN_TRANSFER = 1
    MAX_DAILY = 100 # Максимальная сумма ежедневного бонуса

logger = logging.getLogger(__name__)