import re
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    set_plan, remove_premium, get_premium_users, get_user, get_all_users, get_stats,
    ban_user, unban_user
)
from config import ADMIN_IDS, PLANS

async def admin_add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add <user_id> <duration> (e.g. 1 month, 7 days)")
        return
    target = int(context.args[0])
    dur = ' '.join(context.args[1:]).lower()
    days = 0
    match = re.match(r'(\d+)\s*(day|month|year)s?', dur)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit == 'day':
            days = num
        elif unit == 'month':
            days = num * 30
        elif unit == 'year':
            days = num * 365
    if days == 0:
        await update.message.reply_text("Invalid duration.")
        return
    await set_plan(target, "premium", days)
    await update.message.reply_text(f"✅ Premium added to {target} for {days} days.")

async def admin_remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /rem <user_id>")
        return
    target = int(context.args[0])
    await remove_premium(target)
    await update.message.reply_text(f"✅ Premium removed from {target}.")

async def admin_get_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    users = await get_premium_users()
    if not users:
        await update.message.reply_text("No premium users.")
        return
    text = "👑 **Premium Users**\n\n"
    for uid, plan, expiry in users:
        text += f"• {uid} – {plan.upper()} – Expires: {expiry}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /check <user_id>")
        return
    target = int(context.args[0])
    user = await get_user(target)
    if not user:
        await update.message.reply_text("User not found.")
        return
    await update.message.reply_text(
        f"User: {target}\nPlan: {user['plan']}\nDaily: {user['daily_count']}/{PLANS[user['plan']]['daily_limit']}\nExpiry: {user.get('premium_expiry', 'Never')}\nBanned: {user.get('banned', False)}"
    )

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = ' '.join(context.args)
    users = await get_all_users()
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg)
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    total, premium, banned = await get_stats()
    await update.message.reply_text(
        f"📊 **Stats**\n\nTotal users: {total}\nPremium users: {premium}\nBanned: {banned}",
        parse_mode="Markdown"
    )

async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    target = int(context.args[0])
    await ban_user(target)
    await update.message.reply_text(f"✅ User {target} banned.")

async def admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    target = int(context.args[0])
    await unban_user(target)
    await update.message.reply_text(f"✅ User {target} unbanned.")
