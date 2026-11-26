from flask import Blueprint, request
from telegram import Update

webhook = Blueprint("webhook", __name__)
application = None
event_loop = None


def init_routes(app, loop):
    """Initialize webhook routes with the Telegram Application and event loop."""
    global application, event_loop
    application = app
    event_loop = loop


@webhook.route("/telegram", methods=["POST"])
def telegram_webhook():
    """Webhook endpoint for receiving updates from Telegram."""
    if request.method == "POST":
        update = Update.de_json(request.get_json(), application.bot)
        event_loop.run_until_complete(application.process_update(update))
    return "OK"