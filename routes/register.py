from flask import Blueprint, render_template
import json

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['GET'])
def register():
    # This renders the register.html template which contains the register interface.
    return render_template("register.html", title="Register")

@register_bp.route('/get_items', methods=['GET'])
def get_items():
    try:
        with open("items.json", "r") as file:
            items = json.load(file)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        print(f"Error loading items: {e}")
        return jsonify({"success": False, "message": "Could not load items."})