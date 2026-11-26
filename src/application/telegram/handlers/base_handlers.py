from telegram import Update
from telegram.ext import ContextTypes


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    await update.message.reply_text(
        "Hello! I'm your LED-BOT controller.\n"
        "Use /login <username> <password> to access.\n"
        "Use /help to show all available commands."
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command."""
    help_text = (
        "Available commands:\n\n"
        "Basic Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/login <username> <password> - Login to the system\n"
        "/logout - Logout from the system\n\n"
        "LED Control (logged users only):\n"
        "/ON <led_id> - Turn ON a specific LED\n"
        "/OFF <led_id> - Turn OFF a specific LED\n\n"
        "Example:\n"
        "/login mario password123\n"
        "/ON <led_id>\n"
        "/OFF <led_id>"
    )
    await update.message.reply_text(help_text)


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback handler for unrecognized text messages."""
    await update.message.reply_text(
        "Unknown command. Use /help to see the available commands."
    )