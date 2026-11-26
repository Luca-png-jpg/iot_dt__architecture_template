from datetime import datetime
from flask import current_app
from telegram import Update
from telegram.ext import ContextTypes

# Maps Telegram user_id -> Digital Replica user _id
logged_users = {}


def check_auth(telegram_id: int) -> bool:
    """Return True if the Telegram user is currently authenticated."""
    return telegram_id in logged_users


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /login <username> <password>."""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /login <username> <password>")
        return

    username, password = context.args[0], context.args[1]
    db_service = current_app.config["DB_SERVICE"]

    users = db_service.query_drs(
        "user",
        {"profile.username": username, "profile.password": password},
    )
    if not users:
        await update.message.reply_text("Invalid username or password.")
        return

    user = users[0]
    user_id = user["_id"]
    telegram_id = update.effective_user.id
    logged_users[telegram_id] = user_id

    now = datetime.utcnow()
    db_service.update_dr(
        "user",
        user_id,
        {"data.last_login": now},
    )

    owned_leds = user.get("data", {}).get("owned_leds", [])
    leds_text = "\n".join(f"- {lid}" for lid in owned_leds) if owned_leds else "No LEDs assigned yet."

    await update.message.reply_text(
        f"Login successful! Welcome {username}.\n\nYour assigned LEDs:\n{leds_text}"
    )


async def logout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /logout."""
    telegram_id = update.effective_user.id
    if telegram_id in logged_users:
        del logged_users[telegram_id]
        await update.message.reply_text("You have been logged out.")
    else:
        await update.message.reply_text("You are not logged in.")