from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from routes.utils import jwtVerify

bands_bp = Blueprint('bands', __name__)

DB_FILE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'

@bands_bp.route('/bands', methods=['GET', 'POST'])
def bands():
    user = jwtVerify(request.cookies)
    if not user:
        return redirect(url_for('login.login'))

    if request.method == 'POST' and user.get('role') in ['Admin', 'Vorstand']:
        band_id = request.form.get('band_id')
        name = request.form['name']
        description = request.form.get('description')
        genre = request.form['genre']
        contact_method = request.form['contact_method']
        last_booked = request.form['last_booked']
        comments = request.form['comments']
        bandcamp = request.form.get('bandcamp')
        facebook = request.form.get('facebook')
        instagram = request.form.get('instagram')
        youtube = request.form.get('youtube')
        type_ = request.form.get('type')
        doordeal = request.form.get('doordeal') == 'on'  # Convert checkbox to boolean
        price = request.form.get('price')
        current_logo = request.form.get('current_logo')

        # Handle the logo upload
        logo = request.files.get('logo')
        if logo and logo.filename != '':
            filename = secure_filename(f"{name.lower().replace(' ', '_')}-logo.{logo.filename.split('.')[-1]}")
            logo_path = os.path.join('uploads', filename).replace("\\", "/")
            full_logo_path = os.path.join(UPLOAD_FOLDER, filename)
            logo.save(full_logo_path)
        else:
            logo_path = current_logo

        # Save or update the band data
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if band_id:
            c.execute("""
                UPDATE bands SET name = ?, description = ?, genre = ?, contact_method = ?, last_booked = ?, 
                comments = ?, bandcamp = ?, facebook = ?, instagram = ?, youtube = ?, logo = ?, type = ?, 
                doordeal = ?, price = ? WHERE id = ?
            """, (name, description, genre, contact_method, last_booked, comments, bandcamp, facebook,
                  instagram, youtube, logo_path, type_, doordeal, price, band_id))
        else:
            band_data = (name, description, logo_path, genre, bandcamp, facebook, instagram, youtube,
                         contact_method, last_booked, comments, type_, doordeal, price)
            c.execute("""
                INSERT INTO bands (name, description, logo, genre, bandcamp, facebook, instagram, youtube, 
                contact_method, last_booked, comments, type, doordeal, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, band_data)

        conn.commit()
        conn.close()

        flash("Band information saved successfully!", "success")
        return redirect(url_for('bands.bands'))

    # Fetch all bands data for display
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM bands WHERE type IN ('Band', 'DJ') ORDER BY last_booked DESC")
    bands_data = c.fetchall()
    conn.close()

    return render_template('bands.html', bands=bands_data, active_page='Bands', title='Bands')

@bands_bp.route('/edit_band/<int:band_id>', methods=['GET'])
def edit_band(band_id):
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return "", 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM bands WHERE id = ?', (band_id,))
    band = c.fetchone()
    conn.close()

    if band:
        return jsonify({
            "id": band[0],
            "name": band[1],
            "description": band[2],
            "logo": band[3],
            "genre": band[4],
            "bandcamp": band[5],
            "facebook": band[6],
            "instagram": band[7],
            "youtube": band[8],
            "contact_method": band[9],
            "last_booked": band[10],
            "comments": band[11],
            "type": band[12],
            "doordeal": band[13],
            "price": band[14]
        })
    return "", 404


@bands_bp.route('/delete_band/<int:band_id>', methods=['POST'])
def delete_band(band_id):
    user = jwtVerify(request.cookies)
    if not user or user.get('role') not in ['Admin', 'Vorstand']:
        return "", 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM bands WHERE id = ?', (band_id,))
    conn.commit()
    conn.close()

    flash("Booking deleted successfully!", "success")
    return redirect(url_for('bands.bands'))

@bands_bp.route('/save_email_template', methods=['POST'])
def save_email_template():
    try:
        data = request.get_json()
        email_content = data.get('email_content')

        if not email_content:
            return jsonify(success=False, error="No content provided"), 400

        # Define the target directory and file path
        target_directory = os.path.join(os.getcwd(), "static", "txt")
        file_path = os.path.join(target_directory, "email-template.txt")

        # Ensure the directory exists; if not, create it
        if not os.path.exists(target_directory):
            os.makedirs(target_directory)

        # Write the email content to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(email_content)

        return jsonify(success=True)
    except Exception as e:
        print(f"Error saving email template: {e}")
        return jsonify(success=False, error=str(e)), 500

@bands_bp.route('/get_email_template', methods=['GET'])
def get_email_template():
    file_path = os.path.join(os.getcwd(), "static", "txt", "email-template.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            email_content = file.read()
    except FileNotFoundError:
        email_content = """Hallo [Bandname],

        wir vom Contrast in Konstanz würden euch gerne für einen Auftritt bei uns gewinnen! ..."""  # Default content

    return jsonify(email_content=email_content)


