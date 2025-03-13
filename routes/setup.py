from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from routes.utils import jwtVerify
import os
import json
import logging
import datetime
import sqlite3

setup_bp = Blueprint('setup', __name__)

DB_FILE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'

def today_date():
    # Returns the current date as a string in DD-MM-YYYY format
    return datetime.datetime.now().strftime("%d-%m-%Y")

# -----------------------------------------------------------------
# Database Table Creation
# -----------------------------------------------------------------
def create_stuff_table():
    """
    Creates the stuff table if it does not exist.
    The table stores items for sale without a 'bought' column.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stuff_to_sell (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,  -- JSON string containing detailed item information
                    image_path TEXT,
                    date_added TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    is_intern BOOLEAN NOT NULL DEFAULT 0
                )''')
    conn.commit()
    conn.close()

# Call the function to ensure the table exists
create_stuff_table()

# -----------------------------------------------------------------
# Setup Route
# -----------------------------------------------------------------
@setup_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return redirect(url_for('login.login'))

    config_file = "schema_defaults.json"
    # Load defaults from JSON config file
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            schema_defaults = json.load(f)
    else:
        schema_defaults = {}

    if request.method == 'POST':
        # Save file uploads and get file names
        if request.files.get("organization_logo"):
            logo_file = request.files["organization_logo"]
            logo_path = os.path.join(UPLOAD_FOLDER, logo_file.filename)
            logo_file.save(logo_path)
            schema_defaults["organization_logo"] = logo_file.filename

        if request.files.get("default_image"):
            default_image_file = request.files["default_image"]
            default_image_path = os.path.join(UPLOAD_FOLDER, default_image_file.filename)
            default_image_file.save(default_image_path)
            schema_defaults["default_image"] = default_image_file.filename

        # Save form data to the JSON configuration
        form_data = {
            "organization_name": request.form.get("organization_name"),
            "organization_website": request.form.get("organization_website"),
            "author_name": request.form.get("author_name"),
            "location_name": request.form.get("location_name"),
            "street_address": request.form.get("street_address"),
            "city": request.form.get("city"),
            "postal_code": request.form.get("postal_code"),
            "country": request.form.get("country"),
            "venue_type": request.form.get("venue_type_list"),
            "accessibility": request.form.get("accessibility"),
            "event_status": request.form.get("event_status"),
            "contact_email": request.form.get("contact_email"),
            "contact_phone": request.form.get("contact_phone"),
            # Social Media Links
            "facebook": request.form.get("facebook"),
            "instagram": request.form.get("instagram"),
            "twitter": request.form.get("twitter"),
            "youtube": request.form.get("youtube"),
            "linkedin": request.form.get("linkedin"),
        }

        schema_defaults.update(form_data)

        # Add opening and closing times to schema_defaults
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            day_status = request.form.get(f"{day}_status")
            schema_defaults[f"{day}_status"] = day_status
            
            if day_status == "open":
                opening_time = request.form.get(f"{day}_opening_time")
                closing_time = request.form.get(f"{day}_closing_time")
                if not opening_time or not closing_time:
                    flash(f"Please provide both opening and closing times for {day.capitalize()}.", 'danger')
                    return render_template('setup.html', schema_defaults=schema_defaults, active_page='Setup', title='Setup')
                schema_defaults[f"{day}_opening_time"] = opening_time
                schema_defaults[f"{day}_closing_time"] = closing_time
            elif day_status == "closed":
                schema_defaults[f"{day}_opening_time"] = "00:00"
                schema_defaults[f"{day}_closing_time"] = "00:00"
            elif day_status == "by_appointment":
                schema_defaults[f"{day}_opening_time"] = "ByAppointment"
                schema_defaults[f"{day}_closing_time"] = "ByAppointment"

        try:
            with open(config_file, 'w') as f:
                json.dump(schema_defaults, f, indent=4)
            flash("Defaults updated successfully!", 'success')
        except Exception as e:
            flash(f"Failed to save defaults: {str(e)}", 'danger')

        return render_template('setup.html', schema_defaults=schema_defaults, active_page='Setup', title='Setup')

    return render_template('setup.html', schema_defaults=schema_defaults, active_page='Setup', title='Setup')

# -----------------------------------------------------------------
# Add Item Route
# -----------------------------------------------------------------
@setup_bp.route('/add_item', methods=['POST'])
def add_item():
    data = request.get_json()
    title = data.get("name", "Unnamed Item")
    description = json.dumps(data)
    image_path = data.get("imageDataUrl", "")
    date_added = ""  # Not needed
    user_name = data.get("user_name", "unknown")
    is_intern = 0

    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO stuff_to_sell (title, description, image_path, date_added, user_name, is_intern) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, image_path, date_added, user_name, is_intern)
        )
        conn.commit()
        row_id = c.lastrowid
        conn.close()
        return jsonify({"success": True, "message": "Item saved to DB", "id": row_id})
    except sqlite3.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"})

@setup_bp.route('/get_items', methods=['GET'])
def get_items():
    """
    Endpoint to retrieve all items from the 'stuff' table.
    The description field is stored as a JSON string.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, title, description, image_path, user_name, is_intern FROM stuff_to_sell")
        rows = c.fetchall()
        items = []
        for row in rows:
            # Parse the description JSON string
            try:
                description = json.loads(row[2])
            except Exception:
                description = {}
            items.append({
                "id": row[0],
                "name": row[1],
                "description": description,
                "imageDataUrl": row[3],
                "user_name": row[4],
                "is_intern": row[5]
            })
        conn.close()
        return jsonify({"success": True, "items": items})
    except sqlite3.Error as e:
        return jsonify({"success": False, "message": str(e)})
