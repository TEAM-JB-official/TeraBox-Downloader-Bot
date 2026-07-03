import datetime
import motor.motor_asyncio
from config import MONGO_URL, DB_NAME

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users_col = db.users
settings_col = db.settings
stats_col = db.stats

# ---------- Users ----------
async def get_user(user_id):
    doc = await users_col.find_one({"_id": user_id})
    if not doc:
        return None
    return {
        "plan": doc.get("plan", "free"),
        "daily_count": doc.get("daily_count", 0),
        "last_reset": doc.get("last_reset"),
        "premium_expiry": doc.get("premium_expiry"),
        "join_date": doc.get("join_date"),
        "banned": doc.get("banned", False),
        "referrer": doc.get("referrer"),
        "referral_code": doc.get("referral_code", str(user_id)),
    }

async def create_user(user_id, referrer_id=None):
    today = datetime.date.today().isoformat()
    data = {
        "plan": "free",
        "daily_count": 0,
        "last_reset": today,
        "join_date": today,
        "premium_expiry": None,
        "banned": False,
        "referrer": referrer_id,
        "referral_code": str(user_id),
    }
    await users_col.update_one({"_id": user_id}, {"$setOnInsert": data}, upsert=True)
    if referrer_id:
        await add_referral_bonus(referrer_id)

async def reset_daily_if_needed(user_id):
    today = datetime.date.today().isoformat()
    user = await get_user(user_id)
    if user and user["last_reset"] != today:
        await users_col.update_one({"_id": user_id}, {"$set": {"daily_count": 0, "last_reset": today}})

async def increment_download_count(user_id):
    await users_col.update_one({"_id": user_id}, {"$inc": {"daily_count": 1}})

async def set_plan(user_id, plan, expiry_days=30):
    expiry = (datetime.date.today() + datetime.timedelta(days=expiry_days)).isoformat()
    await users_col.update_one({"_id": user_id}, {"$set": {"plan": plan, "premium_expiry": expiry}})

async def remove_premium(user_id):
    await users_col.update_one({"_id": user_id}, {"$set": {"plan": "free", "premium_expiry": None}})

async def ban_user(user_id):
    await users_col.update_one({"_id": user_id}, {"$set": {"banned": True}})

async def unban_user(user_id):
    await users_col.update_one({"_id": user_id}, {"$set": {"banned": False}})

async def get_all_users():
    cursor = users_col.find({}, {"_id": 1})
    return [doc["_id"] async for doc in cursor]

async def get_premium_users():
    cursor = users_col.find({"plan": {"$ne": "free"}}, {"_id": 1, "plan": 1, "premium_expiry": 1})
    return [(doc["_id"], doc["plan"], doc.get("premium_expiry", "Never")) async for doc in cursor]

async def get_stats():
    total = await users_col.count_documents({})
    premium = await users_col.count_documents({"plan": {"$ne": "free"}})
    banned = await users_col.count_documents({"banned": True})
    return total, premium, banned

# ---------- Referrals ----------
async def add_referral_bonus(user_id):
    from config import REFERRAL_BONUS_DAYS
    user = await get_user(user_id)
    if not user:
        return
    current_expiry = user.get("premium_expiry")
    if current_expiry:
        current = datetime.date.fromisoformat(current_expiry)
        new_expiry = current + datetime.timedelta(days=REFERRAL_BONUS_DAYS)
    else:
        new_expiry = datetime.date.today() + datetime.timedelta(days=REFERRAL_BONUS_DAYS)
        await users_col.update_one({"_id": user_id}, {"$set": {"plan": "premium"}})
    await users_col.update_one({"_id": user_id}, {"$set": {"premium_expiry": new_expiry.isoformat()}})

# ---------- Settings ----------
async def get_settings(user_id):
    doc = await settings_col.find_one({"_id": user_id})
    if not doc:
        return None
    return {
        "thumbnail_file_id": doc.get("thumbnail_file_id"),
        "caption": doc.get("caption"),
        "target_chat_id": doc.get("target_chat_id"),
        "rename_tag": doc.get("rename_tag"),
        "replace_rules": doc.get("replace_rules", {})
    }

async def update_settings(user_id, **kwargs):
    await settings_col.update_one({"_id": user_id}, {"$set": kwargs}, upsert=True)

async def reset_settings(user_id):
    await settings_col.delete_one({"_id": user_id})

# ---------- Stats ----------
async def increment_stat(stat_name):
    today = datetime.date.today().isoformat()
    await stats_col.update_one({"_id": today}, {"$inc": {stat_name: 1}}, upsert=True)

async def get_stat(stat_name, days=30):
    start = datetime.date.today() - datetime.timedelta(days=days)
    cursor = stats_col.find({"_id": {"$gte": start.isoformat()}})
    total = 0
    async for doc in cursor:
        total += doc.get(stat_name, 0)
    return total
