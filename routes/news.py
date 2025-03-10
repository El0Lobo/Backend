from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from routes.utils import jwtVerify  
import json
news_bp = Blueprint('news', __name__)

DB_FILE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
JSON_FOLDER = 'json_data'
# Main news route
@news_bp.route('/', methods=['GET', 'POST'])
@news_bp.route('/news', methods=['GET', 'POST'])
def news():
    # Verify JWT from cookies
    user = jwtVerify(request.cookies)
    if not user:
        return redirect(url_for('login.login'))

    # Load JSON settings for Schema.org defaults
    defaults = load_schema_defaults()

    # Initialize date with the current date
    date = datetime.now().strftime('%Y-%m-%d')

    # Handle new or updated news entry if form is submitted by admin or Vorstand
    if request.method == 'POST' and user.get('role') in ['Admin', 'Vorstand']:
        news_id = request.form.get('news_id')
        title = request.form['title']
        description = request.form['description']
        intern = 'intern' in request.form
        image = request.files.get('image')
        image_path = None

        # Handle image upload
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)
            image_path = filename  # Store only the filename

        # Path for the JSON file
        json_filename = f"news_{news_id}.json"
        json_path = os.path.join(JSON_FOLDER, json_filename)

        # Insert or update news item
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if news_id:  # Update existing news
            # Fetch the current `intern` status of the entry
            c.execute("SELECT intern FROM news WHERE id = ?", (news_id,))
            old_intern = bool(c.fetchone()[0])

            # Delete JSON if changing from non-intern to intern
            if intern and not old_intern and os.path.exists(json_path):
                os.remove(json_path)
            # Create or update JSON if changing from intern to non-intern
            elif not intern and old_intern:
                json_ld = generate_schema_json(title, description, date, image_path, defaults)
                with open(json_path, 'w') as json_file:
                    json.dump(json_ld, json_file, indent=4)

            # Update the news entry
            c.execute("UPDATE news SET title = ?, description = ?, intern = ?, image_path = ? WHERE id = ?",
                      (title, description, intern, image_path, news_id))
        else:  # Add new news entry
            c.execute("INSERT INTO news (title, description, date, image_path, intern) VALUES (?, ?, ?, ?, ?)",
                      (title, description, date, image_path, intern))
            news_id = c.lastrowid

            # Only create JSON if the new entry is not intern
            if not intern:
                json_ld = generate_schema_json(title, description, date, image_path, defaults)
                with open(json_path, 'w') as json_file:
                    json.dump(json_ld, json_file, indent=4)
        
        conn.commit()
        conn.close()

        return redirect(url_for('news.news', active_page='News', title='News'))

    # Fetch news items from the database for the main news page
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM news ORDER BY date DESC")
    news_items = c.fetchall()
    conn.close()

    # Convert the date string to a datetime object for each news item
    formatted_news_items = [
        {
            "id": item[0],
            "title": item[1],
            "description": item[2],
            "date": datetime.strptime(item[3], '%Y-%m-%d'),
            "image_path": item[4],
            "intern": item[5]
        }
        for item in news_items
    ]

    return render_template('news.html', news_items=formatted_news_items, schema_defaults=defaults, active_page='News', title='News')

def generate_schema_json(title, description, date, image_path, defaults):
    """Generate Schema.org JSON-LD for a news article or event."""
    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",  # This could also be "Event" for live music or similar
        "headline": title,
        "description": description,
        "datePublished": date,
        "publisher": {
            "@type": "Organization",
            "name": defaults.get("organization_name", "Your Organization Name"),
            "url": defaults.get("organization_website", "https://example.com"),
            "logo": {
                "@type": "ImageObject",
                "url": defaults.get("organization_logo", "https://example.com/logo.png")
            }
        },
        "author": {
            "@type": "Person",
            "name": defaults.get("author_name", "Admin")
        },
        "image": image_path if image_path else defaults.get("default_image", None),
        "location": {
            "@type": "Place",
            "name": defaults.get("location_name", "Default Venue"),
            "address": {
                "@type": "PostalAddress",
                "streetAddress": defaults.get("street_address", "123 Default St"),
                "addressLocality": defaults.get("city", "Default City"),
                "postalCode": defaults.get("postal_code", "12345"),
                "addressCountry": defaults.get("country", "DE")
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": defaults.get("latitude", 0.0),
                "longitude": defaults.get("longitude", 0.0)
            }
        },
        "accessibility": defaults.get("accessibility", "Wheelchair Accessible"),
        "eventStatus": defaults.get("event_status", "https://schema.org/EventScheduled")
    }

    return schema

def load_schema_defaults():
    """Load the default schema settings from a configuration file."""
    config_file = "schema_defaults.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

@news_bp.route('/setup_schema_defaults', methods=['GET', 'POST'])
def setup_schema_defaults():
    # Verify JWT from cookies to ensure only admins can access
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return redirect(url_for('login.login'))

    config_file = "schema_defaults.json"

    if request.method == 'POST':
        # Save the new defaults to the JSON configuration file
        schema_defaults = {
            "organization_name": request.form.get("organization_name"),
            "organization_website": request.form.get("organization_website"),
            "organization_logo": request.form.get("organization_logo"),
            "author_name": request.form.get("author_name"),
            "location_name": request.form.get("location_name"),
            "street_address": request.form.get("street_address"),
            "city": request.form.get("city"),
            "postal_code": request.form.get("postal_code"),
            "country": request.form.get("country"),
            "latitude": float(request.form.get("latitude", 0.0)),
            "longitude": float(request.form.get("longitude", 0.0)),
            "accessibility": request.form.get("accessibility"),
            "event_status": request.form.get("event_status"),
            "default_image": request.form.get("default_image")
        }

        with open(config_file, 'w') as f:
            json.dump(schema_defaults, f, indent=4)

        flash("Defaults updated successfully!", 'success')
        return redirect(url_for('news.news'))

    # Load current settings if they exist
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            schema_defaults = json.load(f)
    else:
        schema_defaults = {}

    return render_template('setup_schema_defaults.html', schema_defaults=schema_defaults)


# Edit news route
@news_bp.route('/edit/<int:news_id>', methods=['GET'])
def edit_news(news_id):
    # Verify JWT from cookies to ensure only admins or Vorstand can edit the form
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return "", 403

    # Fetch the current data for the news item
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM news WHERE id = ?', (news_id,))
    news_item = c.fetchone()
    conn.close()

    if news_item:
        return jsonify({
            "id": news_item[0],
            "title": news_item[1],
            "description": news_item[2],
            "intern": bool(news_item[5])
        })
    return "", 404

@news_bp.route('/delete/<int:news_id>', methods=['DELETE'])
def delete_news(news_id):
    # Verify JWT from cookies to ensure only admins or Vorstand can delete news
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return jsonify({"error": "Unauthorized"}), 403

    # Delete the news item from the database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT intern FROM news WHERE id = ?", (news_id,))
    intern_status = bool(c.fetchone()[0])
    c.execute("DELETE FROM news WHERE id = ?", (news_id,))
    conn.commit()
    conn.close()

    # Delete JSON file if it was a non-intern entry
    if not intern_status:
        json_filename = f"news_{news_id}.json"
        json_path = os.path.join(JSON_FOLDER, json_filename)
        if os.path.exists(json_path):
            os.remove(json_path)

    return jsonify({"message": f"Deleted news {news_id}"}), 200


@news_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)