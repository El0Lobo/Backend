from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from routes.utils import jwtVerify  

stuff_bp = Blueprint('stuff', __name__)

UPLOAD_FOLDER = 'static/uploads'
PUBLIC_JSON_PATH = 'stuff_public.json'
DB_FILE = 'database.db'

# Function to save public items to JSON for the website
def save_public_stuff_to_json(public_data):
    with open(PUBLIC_JSON_PATH, 'w') as file:
        json.dump(public_data, file, indent=2)

# Load public items from the database for JSON export
def load_public_stuff():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM stuff WHERE is_intern = 0 AND bought = 0")
    public_data = [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "image_path": row[3],
            "date_added": datetime.strptime(row[4], '%Y-%m-%d'),
            "user_name": row[6],
            "is_intern": bool(row[7]),
            "bought": bool(row[5])
        }
        for row in c.fetchall()
    ]
    conn.close()
    return public_data

# Route to handle the "Stuff" page
@stuff_bp.route('/stuff', methods=['GET', 'POST'])
def stuff():
    # Verify JWT from cookies and check for valid roles
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand', 'Manager', 'User']:
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == 'POST':
        user_name = user.get("name", "Unknown")
        title = request.form.get('title')
        description = request.form.get('description')
        is_intern = bool(request.form.get('intern'))
        image = request.files.get('image')

        image_path = None
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(image_path)

        # Insert new item into the database with date_added formatted as 'YYYY-MM-DD'
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        date_added = datetime.now().strftime('%Y-%m-%d')
        c.execute("""
            INSERT INTO stuff (title, description, image_path, date_added, user_name, is_intern)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, description, image_path, date_added, user_name, is_intern))
        conn.commit()
        conn.close()

        # Save non-internal entries to the public JSON file
        if not is_intern:
            public_data = load_public_stuff()
            save_public_stuff_to_json(public_data)

        return redirect(url_for('stuff.stuff'))

    # Fetch needed items
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM stuff WHERE bought = 0 ORDER BY date_added DESC")
    needed_stuff_data = [
        {
            "id": item[0],
            "title": item[1],
            "description": item[2],
            "image_path": item[3],
            "date_added": datetime.strptime(item[4], '%Y-%m-%d'),  # Parse date as datetime object
            "user_name": item[6],
            "is_intern": bool(item[7]),
            "bought": bool(item[5])
        }
        for item in c.fetchall()
    ]

    # Fetch bought items
    c.execute("SELECT * FROM stuff WHERE bought = 1 ORDER BY date_added DESC")
    bought_stuff_data = [
        {
            "id": item[0],
            "title": item[1],
            "description": item[2],
            "image_path": item[3],
            "date_added": datetime.strptime(item[4], '%Y-%m-%d'),  # Parse date as datetime object
            "user_name": item[6],
            "is_intern": bool(item[7]),
            "bought": bool(item[5])
        }
        for item in c.fetchall()
    ]
    conn.close()

    return render_template('stuff.html', user=user, stuff_data=needed_stuff_data, bought_stuff_data=bought_stuff_data, active_page='Stuff', title='Stuff')

# Route to mark an item as bought
@stuff_bp.route('/mark_bought/<int:stuff_id>', methods=['POST'])
def mark_bought(stuff_id):
    # Verify JWT from cookies and check for authorized roles
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand', 'Manager']:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE stuff SET bought = 1 WHERE id = ?", (stuff_id,))
    conn.commit()
    conn.close()

    # Update public JSON if the item is non-internal
    public_data = load_public_stuff()
    save_public_stuff_to_json(public_data)

    return jsonify({"success": True, "message": "Item marked as bought"})
