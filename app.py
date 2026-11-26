import asyncio
import nest_asyncio
from flask import Flask
from flask_cors import CORS
from pyngrok import ngrok
from pyngrok.exception import PyngrokNgrokError
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.virtualization.digital_replica.schema_registry import SchemaRegistry
from src.services.database_service import DatabaseService
from src.digital_twin.dt_factory import DTFactory
from src.application.api import register_api_blueprints
from src.application.led_apis import register_led_blueprint
from src.application.user_led_apis import register_user_blueprint
from src.application.mqtt_handler import MQTTHandler
from config.config_loader import ConfigLoader

from src.application.telegram.config.settings import (
    TELEGRAM_TOKEN,
    NGROK_TOKEN,
    SERVER_HOST,
    SERVER_PORT,
    WEBHOOK_PATH,
)
from src.application.telegram.routes.webhook_routes import webhook, init_routes
from src.application.telegram.handlers.base_handlers import (
    start_handler,
    help_handler,
    echo_handler,
)
from src.application.telegram.handlers.login_handlers import (
    login_handler,
    logout_handler,
)
from src.application.telegram.handlers.led_handlers import (
    led_on_handler,
    led_off_handler,
)

# Allow nested event loops when Flask handles Telegram webhook updates
nest_asyncio.apply()


class FlaskServer:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        self.loop = None
        self.telegram_app = None
        self.public_url = None
        self._init_components()
        self._register_blueprints()

    def _init_components(self):
        """Initialize all required components and store them in app config"""
        schema_registry = SchemaRegistry()
        schema_registry.load_schema("led", "src/virtualization/templates/LED.yaml")
        schema_registry.load_schema("user", "src/virtualization/templates/user.yaml")

        # Load database configuration
        db_config = ConfigLoader.load_database_config()
        connection_string = ConfigLoader.build_connection_string(db_config)

        # Initialize DatabaseService with populated schema_registry
        db_service = DatabaseService(
            connection_string=connection_string,
            db_name=db_config["settings"]["name"],
            schema_registry=schema_registry,
        )
        db_service.connect()

        # Initialize DTFactory
        dt_factory = DTFactory(db_service, schema_registry)

        # Initialize and start MQTT publisher for LED commands
        mqtt_handler = MQTTHandler()
        mqtt_handler.start()

        # Store references
        self.app.config["SCHEMA_REGISTRY"] = schema_registry
        self.app.config["DB_SERVICE"] = db_service
        self.app.config["DT_FACTORY"] = dt_factory
        self.app.config["MQTT_HANDLER"] = mqtt_handler

    def _register_blueprints(self):
        """Register all API blueprints"""
        register_api_blueprints(self.app)
        register_led_blueprint(self.app)
        register_user_blueprint(self.app)
        self.app.register_blueprint(webhook)

    def _setup_telegram_handlers(self, application: Application):
        """Register all Telegram bot command and message handlers"""
        application.add_handler(CommandHandler("start", start_handler))
        application.add_handler(CommandHandler("help", help_handler))
        application.add_handler(CommandHandler("login", login_handler))
        application.add_handler(CommandHandler("logout", logout_handler))
        application.add_handler(CommandHandler("ON", led_on_handler))
        application.add_handler(CommandHandler("OFF", led_off_handler))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler)
        )

    def run(self, host=SERVER_HOST, port=SERVER_PORT, debug=True, use_reloader=False):
        """Run the Flask server with Telegram webhook and ngrok tunnel"""
        try:
            # Create persistent event loop and start Telegram Application
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
            self._setup_telegram_handlers(self.telegram_app)

            self.loop.run_until_complete(self.telegram_app.initialize())
            self.loop.run_until_complete(self.telegram_app.start())

            # Open ngrok tunnel and configure Telegram webhook
            try:
                ngrok.set_auth_token(NGROK_TOKEN)
            except PyngrokNgrokError as e:
                if "already set" not in str(e).lower():
                    raise

            self.public_url = ngrok.connect(port).public_url
            webhook_url = f"{self.public_url}{WEBHOOK_PATH}"
            print(f"Webhook URL: {webhook_url}")
            self.loop.run_until_complete(self.telegram_app.bot.set_webhook(webhook_url))

            init_routes(self.telegram_app, self.loop)

            # Explicitly forward use_reloader so Flask does not spawn duplicate ngrok/MQTT sessions
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=use_reloader,
            )
        finally:
            # Cleanup on server shutdown
            if self.public_url:
                ngrok.disconnect(self.public_url)
            if self.telegram_app and self.loop:
                if self.telegram_app.running:
                    self.loop.run_until_complete(self.telegram_app.stop())
                self.loop.run_until_complete(self.telegram_app.shutdown())
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            if "MQTT_HANDLER" in self.app.config:
                self.app.config["MQTT_HANDLER"].stop()
            if "DB_SERVICE" in self.app.config:
                self.app.config["DB_SERVICE"].disconnect()


if __name__ == "__main__":
    server = FlaskServer()
    server.run()