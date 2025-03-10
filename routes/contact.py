from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import sqlite3

contact_bp = Blueprint('contact', __name__)
DB_FILE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@contact_bp.route('/contact', methods=['GET', 'POST'])
def manage_contacts():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if request.method == 'POST':
            contact_id = request.form.get('id')
            category = request.form['category']
            name = request.form['name']
            email = request.form.get('email', '')
            phone = request.form.get('phone', '')
            details = request.form.get('details', '')
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            url = request.form.get('url', '')
            notes = request.form.get('notes', '')

            if contact_id:  # Update existing contact
                c.execute('''UPDATE contacts 
                             SET category=?, name=?, email=?, phone=?, details=?, 
                                 username=?, password=?, url=?, notes=? 
                             WHERE id=?''',
                          (category, name, email, phone, details, username, password, url, notes, contact_id))
            else:  # Add new contact
                c.execute('''INSERT INTO contacts (category, name, email, phone, details, 
                                                    username, password, url, notes)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (category, name, email, phone, details, username, password, url, notes))
            conn.commit()

        c.execute("SELECT * FROM contacts ORDER BY category, name")
        contacts = [dict(row) for row in c.fetchall()]
        return render_template('contact.html', contacts=contacts, active_page='Credentials', title='Credentials')

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        if conn:
            conn.close()

@contact_bp.route('/contacts/delete/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        return redirect(url_for('contact.manage_contacts'))
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred"}), 500
    
    finally:
        if conn:
            conn.close()

@contact_bp.route('/contacts/edit/<int:contact_id>', methods=['GET'])
def get_contact(contact_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
        contact = c.fetchone()
        
        if contact:
            return jsonify(dict(contact))
        else:
            return jsonify({"error": "Contact not found"}), 404

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred"}), 500

    finally:
        if conn:
            conn.close()
