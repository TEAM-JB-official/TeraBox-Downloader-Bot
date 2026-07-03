import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://summer-cell-a956.crezybotz.workers.dev/?url="
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = "terabox_bot"
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")  # e.g., "-1001234567890"
REFERRAL_BONUS_DAYS = int(os.getenv("REFERRAL_BONUS_DAYS", 3))
PORT = int(os.getenv("PORT", 8000))

PLANS = {
    "free": {"daily_limit": 3, "size_limit_mb": 4096},
    "premium": {"daily_limit": 50, "size_limit_mb": 4096},
    "vip": {"daily_limit": 100, "size_limit_mb": 4096},
}

MAX_SINGLE_FILE_MB = 1900      # 1.9 GB – Telegram supports up to 2 GB for documents
SPLIT_SIZE_MB = 50             # split into 50 MB parts if above threshold
MAX_CONCURRENT_JOBS = 1
