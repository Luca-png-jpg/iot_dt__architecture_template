import re
from datetime import datetime
from flask import current_app
from telegram import Update
from telegram.ext import ContextTypes
from src.application.telegram.handlers.login_handlers import check_auth, logged_users


async def _set_led_state(update: Update, command: str, target_state: str):
    """Shared logic for turning a LED on or off."""
    try:
        telegram_id = update.effective_user.id
        if not check_auth(telegram_id):
            await update.message.reply_text(
                "Please login first using /login <username> <password>"
            )
            return

        message = update.message.text.strip()
        match = re.match(rf"/{command}\s+([^\s]+)", message)
        if not match:
            await update.message.reply_text(
                f"Invalid format! Use: /{command} <led_id>"
            )
            return

        led_id = match.group(1)
        db_service = current_app.config["DB_SERVICE"]

        user = db_service.get_dr("user", logged_users[telegram_id])
        if not user or led_id not in user.get("data", {}).get("owned_leds", []):
            await update.message.reply_text("You don't own this LED!")
            return

        led = db_service.get_dr("led", led_id)
        if not led:
            await update.message.reply_text("LED not found!")
            return

        current_time = datetime.utcnow()
        measurements = led.get("data", {}).get("measurements", [])
        measurements.append({
            "type": "state_change",
            "value": 1.0 if target_state == "on" else 0.0,
            "timestamp": current_time,
        })

        metadata = dict(led.get("metadata", {}))
        metadata["updated_at"] = current_time
        metadata["last_status_change"] = current_time

        update_data = {
            "data.state": target_state,
            "data.controlled_by": f"telegram_{telegram_id}",
            "data.measurements": measurements,
            "metadata": metadata,
        }
        db_service.update_dr("led", led_id, update_data)

        mqtt_handler = current_app.config["MQTT_HANDLER"]
        mqtt_handler.publish_led_state(led_id, target_state)

        await update.message.reply_text(
            f"LED {led_id} turned {target_state.upper()}!"
        )
    except Exception as e:
        await update.message.reply_text(f"Error updating LED: {str(e)}")


async def led_on_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ON <led_id> command."""
    await _set_led_state(update, "ON", "on")


async def led_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /OFF <led_id> command."""
    await _set_led_state(update, "OFF", "off")