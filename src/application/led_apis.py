from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from src.virtualization.digital_replica.dr_factory import DRFactory

led_api = Blueprint("led_api", __name__, url_prefix="/api/led")


def register_led_blueprint(app):
    """Register LED API blueprint with Flask app."""
    app.register_blueprint(led_api)


@led_api.route("/", methods=["POST"])
def create_led():
    """Create a new LED Digital Replica."""
    try:
        data = request.get_json()
        required_fields = ["name", "location"]
        if not data or not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        now = datetime.utcnow()
        initial_data = {
            "profile": {
                "name": data["name"],
                "location": data["location"],
                "description": data.get("description", ""),
            },
            "metadata": {
                "status": "active",
                "last_status_change": now,
            },
            "data": {
                "state": "off",
                "brightness": 0,
                "measurements": [],
                "controlled_by": "system",
            },
        }

        dr_factory = DRFactory("src/virtualization/templates/LED.yaml")
        led_dr = dr_factory.create_dr("led", initial_data)
        led_id = current_app.config["DB_SERVICE"].save_dr("led", led_dr)

        return jsonify({
            "led_id": led_id,
            "message": "LED created successfully",
            "status": "success",
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@led_api.route("/<led_id>", methods=["GET"])
def get_led(led_id):
    """Get LED details."""
    try:
        led = current_app.config["DB_SERVICE"].get_dr("led", led_id)
        if not led:
            return jsonify({"error": "LED not found"}), 404
        return jsonify(led), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500