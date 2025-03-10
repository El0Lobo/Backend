from flask import Blueprint, render_template, redirect, url_for, request, flash
from routes.utils import jwtVerify
import os
import json
import logging

setup_bp = Blueprint('setup', __name__)

UPLOAD_FOLDER = 'static/uploads'

# Load the default schema settings from a configuration file
def load_schema_defaults():
    """Load the default schema settings from a configuration file."""
    config_file = "schema_defaults.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

@setup_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return redirect(url_for('login.login'))

    config_file = "schema_defaults.json"
    schema_defaults = load_schema_defaults()

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
                
                # Backend validation to ensure both times are provided
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

        # Write updated values to the JSON file
        try:
            with open(config_file, 'w') as f:
                json.dump(schema_defaults, f, indent=4)
            flash("Defaults updated successfully!", 'success')
        except Exception as e:
            flash(f"Failed to save defaults: {str(e)}", 'danger')

        return render_template('setup.html', schema_defaults=schema_defaults, active_page='Setup', title='Setup')

    return render_template('setup.html', schema_defaults=schema_defaults, active_page='Setup', title='Setup')
