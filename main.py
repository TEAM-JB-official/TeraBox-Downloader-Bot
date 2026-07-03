import asyncio
import logging
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from config import BOT_TOKEN, ADMIN_IDS, PLANS, FORCE_CHANNEL, PORT
from database import (
    get_user, create_user, reset_daily_if_needed, increment_download_count,
    get_settings, ban_user, unban_user, get_all_users, get_premium_users, get_stats,
    set_plan, remove_premium, increment_stat
)
from handlers import user, admin
from utils import fetch_terabox_data, apply_rename_and_replace, get_file_type
from downloader import download_and_upload_stream
import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Semaphore to limit concurrency
semaphore = asyncio.Semaphore(1)

# ---------- Middleware: Force Subscribe ----------
async def force_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FORCE_CHANNEL:
        return True
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_CHANNEL, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_CHANNEL}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("You must join our channel to use this bot.", reply_markup=reply_markup)
    return False

# ---------- Link Handler ----------
async def handle_terabox_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_subscribe(update, context):
        return

    user_id = update.effective_user.id
    link = update.message.text.strip()

    user = await get_user(user_id)
    if not user:
        await create_user(user_id)
        user = await get_user(user_id)

    if user.get("banned", False):
        await update.message.reply_text("You are banned from using this bot.")
        return

    await reset_daily_if_needed(user_id)
    remaining = PLANS[user["plan"]]["daily_limit"] - user["daily_count"]
    if remaining <= 0:
        await update.message.reply_text("❌ Daily limit reached. Upgrade or wait.")
        return

    wait_msg = await update.message.reply_text("⏳ Fetching file info...")
    data = await fetch_terabox_data(link)
    if not data or not data.get("download_link"):
        await wait_msg.edit_text("❌ No download link available.")
        return

    download_link = data["download_link"]
    size_bytes = int(data.get("size_bytes", 0))
    size_limit = PLANS[user["plan"]]["size_limit_mb"] * 1024 * 1024
    if size_bytes > size_limit:
        await wait_msg.edit_text(f"❌ File too large ({data.get('size_human')}). Limit: {PLANS[user['plan']]['size_limit_mb']} MB.")
        return

    original_filename = data.get("title", "file")
    settings = await get_settings(user_id) or {}
    filename = apply_rename_and_replace(original_filename, settings.get("rename_tag"), settings.get("replace_rules", {}))
    caption = settings.get("caption")
    if caption:
        caption = caption.replace("{filename}", filename)
    else:
        caption = f"📁 {filename}\n📦 {data.get('size_human')}"

    thumbnail = settings.get("thumbnail_file_id")
    target_chat = settings.get("target_chat_id") or user_id

    await wait_msg.delete()

    progress_msg = await context.bot.send_message(chat_id=user_id, text="⏳ Starting...")

    async with semaphore:
        try:
            success = await download_and_upload_stream(
                chat_id=target_chat,
                download_url=download_link,
                filename=filename,
                caption=caption,
                progress_msg=progress_msg,
                thumbnail=thumbnail,
                total_size=size_bytes
            )
            if success:
                await increment_download_count(user_id)
                await increment_stat("downloads")
                # Direct download button
                keyboard = [[InlineKeyboardButton("⬇️ Download Full File (External)", url=download_link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=user_id,
                    text="📎 **You can also download the complete file directly from Terabox.**",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        except Exception as e:
            await progress_msg.edit_text(f"❌ Error: {e}")
            logger.error(f"Error: {e}")

async def unknown(update, context):
    await update.message.reply_text("Unknown command. Use /help.")

# ---------- Main ----------
async def main():
    # Start web server for health check (in background)
    asyncio.create_task(web.run_web_server(PORT))

    request = HTTPXRequest(read_timeout=120.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    # Register handlers
    app.add_handler(CommandHandler("start", user.start))
    app.add_handler(CommandHandler("help", user.help_command))
    app.add_handler(CommandHandler("account", user.account_command))
    app.add_handler(CommandHandler("myplan", user.myplan_command))
    app.add_handler(CommandHandler("plans", user.plans_command))
    app.add_handler(CommandHandler("terms", user.terms_command))
    app.add_handler(CommandHandler("settings", user.settings_command))
    app.add_handler(CommandHandler("setthumb", user.set_thumbnail))
    app.add_handler(CommandHandler("removethumb", user.remove_thumbnail))
    app.add_handler(CommandHandler("setcaption", user.set_caption))
    app.add_handler(CommandHandler("resetcaption", user.reset_caption))
    app.add_handler(CommandHandler("setchat", user.set_chat))
    app.add_handler(CommandHandler("resetchat", user.reset_chat))
    app.add_handler(CommandHandler("replace", user.set_replace))
    app.add_handler(CommandHandler("removereplace", user.remove_replace))
    app.add_handler(CommandHandler("setrename", user.set_rename))
    app.add_handler(CommandHandler("resetrename", user.reset_rename))

    # Admin commands
    app.add_handler(CommandHandler("add", admin.admin_add_premium))
    app.add_handler(CommandHandler("rem", admin.admin_remove_premium))
    app.add_handler(CommandHandler("get", admin.admin_get_premium))
    app.add_handler(CommandHandler("check", admin.admin_check_user))
    app.add_handler(CommandHandler("broadcast", admin.admin_broadcast))
    app.add_handler(CommandHandler("stats", admin.admin_stats))
    app.add_handler(CommandHandler("ban", admin.admin_ban_user))
    app.add_handler(CommandHandler("unban", admin.admin_unban_user))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_terabox_link))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("🤖 Bot started – low‑RAM mode, web server on port %s", PORT)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
