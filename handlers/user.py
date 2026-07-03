from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, create_user, reset_daily_if_needed, get_settings, update_settings
from config import PLANS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    referrer = int(args[0]) if args and args[0].isdigit() else None
    await create_user(user_id, referrer)
    await update.message.reply_text("👋 Welcome! Use /help for commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 **Commands**\n\n"
        "/account – Your ID\n"
        "/myplan – Your plan & usage\n"
        "/plans – Available plans\n"
        "/terms – Terms\n"
        "/settings – View your settings\n"
        "/setthumb – Set thumbnail (reply to photo)\n"
        "/removethumb – Remove thumbnail\n"
        "/setcaption – Set custom caption (use {filename})\n"
        "/resetcaption – Remove caption\n"
        "/setchat – Set target chat ID\n"
        "/resetchat – Reset to DM\n"
        "/replace old=new – Add replace rule\n"
        "/removereplace old – Remove rule\n"
        "/setrename – Set rename tag (use {filename})\n"
        "/resetrename – Remove rename tag\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def myplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await create_user(user_id)
        user = await get_user(user_id)
    await reset_daily_if_needed(user_id)
    plan = user["plan"]
    daily_limit = PLANS[plan]["daily_limit"]
    used = user["daily_count"]
    expiry = user.get("premium_expiry") or "Never"
    await update.message.reply_text(
        f"📊 **Plan:** {plan.upper()}\n"
        f"📥 Today: {used}/{daily_limit}\n"
        f"⏳ Expires: {expiry}\n"
        f"📦 Max file size: {PLANS[plan]['size_limit_mb']} MB"
    )

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💰 **Plans**\n\n"
    for name, details in PLANS.items():
        text += f"• {name.upper()}: {details['daily_limit']} downloads/day, {details['size_limit_mb']} MB/file\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 Use responsibly. Don't share copyrighted content. Limits apply.")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = await get_settings(user_id)
    if not settings:
        await update.message.reply_text("All settings are default.")
        return
    text = "⚙️ **Settings**\n\n"
    text += f"Thumbnail: {'✅' if settings['thumbnail_file_id'] else '❌'}\n"
    text += f"Custom caption: {'✅' if settings['caption'] else '❌'}\n"
    text += f"Target chat: {settings['target_chat_id'] or 'DM'}\n"
    text += f"Rename tag: {settings['rename_tag'] or 'None'}\n"
    text += f"Replace rules: {len(settings['replace_rules'])} active"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- Settings commands ----------
async def set_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Reply to an image with /setthumb")
        return
    file_id = update.message.reply_to_message.photo[-1].file_id
    await update_settings(user_id, thumbnail_file_id=file_id)
    await update.message.reply_text("✅ Thumbnail set.")

async def remove_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_settings(user_id, thumbnail_file_id=None)
    await update.message.reply_text("✅ Thumbnail removed.")

async def set_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setcaption Your caption (use {filename})")
        return
    caption = ' '.join(context.args)
    await update_settings(user_id, caption=caption)
    await update.message.reply_text("✅ Caption set.")

async def reset_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_settings(user_id, caption=None)
    await update.message.reply_text("✅ Caption removed.")

async def set_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setchat <chat_id>")
        return
    chat_id = int(context.args[0])
    await update_settings(user_id, target_chat_id=chat_id)
    await update.message.reply_text(f"✅ Target chat set to {chat_id}.")

async def reset_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_settings(user_id, target_chat_id=None)
    await update.message.reply_text("✅ Reset to DM.")

async def set_replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args or '=' not in context.args[0]:
        await update.message.reply_text("Usage: /replace old=new")
        return
    old, new = context.args[0].split('=', 1)
    settings = await get_settings(user_id) or {}
    rules = settings.get("replace_rules", {})
    rules[old] = new
    await update_settings(user_id, replace_rules=rules)
    await update.message.reply_text(f"✅ Rule added: '{old}' → '{new}'")

async def remove_replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /removereplace old")
        return
    old = context.args[0]
    settings = await get_settings(user_id) or {}
    rules = settings.get("replace_rules", {})
    if old in rules:
        del rules[old]
        await update_settings(user_id, replace_rules=rules)
        await update.message.reply_text(f"✅ Rule removed: '{old}'")
    else:
        await update.message.reply_text("Rule not found.")

async def set_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setrename tag (use {filename})")
        return
    tag = ' '.join(context.args)
    await update_settings(user_id, rename_tag=tag)
    await update.message.reply_text(f"✅ Rename tag set: {tag}")

async def reset_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update_settings(user_id, rename_tag=None)
    await update.message.reply_text("✅ Rename tag removed.")
