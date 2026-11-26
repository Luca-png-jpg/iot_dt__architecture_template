from flask import Blueprint, request, jsonify, current_app
from src.virtualization.digital_replica.dr_factory import DRFactory

user_api = Blueprint("user_api", __name__, url_prefix="/api/user")


def register_user_blueprint(app):
    """Register User API blueprint with Flask app."""
    app.register_blueprint(user_api)


@user_api.route("/register", methods=["POST"])
def register_user():
    """Register a new user."""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ["username", "password"]):
            return jsonify({"error": "Missing username or password"}), 400

        db_service = current_app.config["DB_SERVICE"]
        existing = db_service.query_drs("user", {"profile.username": data["username"]})
        if existing:
            return jsonify({"error": "Username already exists"}), 409

        initial_data = {
            "profile": {
                "username": data["username"],
                "password": data["password"],
            },
            "metadata": {"status": "active"},
            "data": {"owned_leds": []},
        }

        dr_factory = DRFactory("src/virtualization/templates/user.yaml")
        user_dr = dr_factory.create_dr("user", initial_data)
        user_id = db_service.save_dr("user", user_dr)

        return jsonify({
            "user_id": user_id,
            "message": "User registered successfully",
            "status": "success",
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@user_api.route("/<user_id>/assign/<led_id>", methods=["POST"])
def assign_led(user_id, led_id):
    """Assign a LED to a user."""
    try:
        db_service = current_app.config["DB_SERVICE"]
        user = db_service.get_dr("user", user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        led = db_service.get_dr("led", led_id)
        if not led:
            return jsonify({"error": "LED not found"}), 404

        owned_leds = user.get("data", {}).get("owned_leds", [])
        if led_id not in owned_leds:
            owned_leds.append(led_id)
            db_service.update_dr("user", user_id, {"data.owned_leds": owned_leds})

        return jsonify({
            "message": "LED assigned successfully",
            "user_id": user_id,
            "led_id": led_id,
            "status": "success",
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500