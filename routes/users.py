from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import bcrypt
from datetime import datetime, timedelta

users_bp = Blueprint('users', __name__)

DB_FILE = 'database.db'

# Helper function to format date
def format_date(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            return date_str  # Return as-is if parsing fails
    return None

# Helper function to check if payment is valid
def is_payment_valid(paid_until):
    if paid_until:
        try:
            return datetime.strptime(paid_until, "%Y-%m-%d") >= datetime.now()
        except ValueError:
            return False
    return False

@users_bp.route('/users', methods=['GET', 'POST'])
def users():
    if 'logged_in' not in session or not session['logged_in'] or session['role'] not in ['Admin', 'Vorstand']:
        return redirect(url_for('login.login'))

    # Fetch all users from the database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, name, nickname, phone, email, password, role, 
                 show_email, show_phone, has_key, paid, street, number, city, 
                 postcode, birthday, patron, patron_amount, paid_until, member_since, show_birthday, description 
                 FROM users ORDER BY role""")
    users = c.fetchall()
    conn.close()

    # Get today's date in DD.MM format
    today = datetime.now().strftime('%m-%d')  # Compare with MM-DD
    users = [
        list(user[:15]) + [
            format_date(user[15]),  # Format birthday
            user[16],  # Patron status
            user[17],  # Patron amount
            format_date(user[18]),  # Format paid_until
            is_payment_valid(user[18]),  # Payment validity
            (datetime.strptime(user[15], '%Y-%m-%d').strftime('%m-%d') == today) if user[15] else False,  # Birthday match
            format_date(user[19]),  # Format member_since
            bool(user[20]),  # Show birthday
            user[21]  # Description (Added this)
        ]
        for user in users
    ]



    if request.method == 'POST':
        # Retrieve form data
        user_id = request.form.get('user_id')
        name = request.form['name']
        nickname = request.form['nickname']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form.get('password', '')
        role = request.form['role']
        show_email = 'show_email' in request.form
        show_phone = 'show_phone' in request.form
        has_key = 'has_key' in request.form
        paid = 1 if 'paid' in request.form else 0  # Convert to integer
        street = request.form['street']
        number = request.form['number']
        city = request.form['city']
        postcode = request.form['postcode']
        birthday = request.form.get('birth-date')
        patron = 1 if 'patron' in request.form else 0  # Convert to integer
        patron_amount = request.form.get('patron-amount', 0)
        paid_duration = int(request.form.get('paid-duration', 0))  # Duration in months
        member_since = request.form.get('member-since')
        show_birthday = 1 if 'show_birthday' in request.form else 0
        paid_until = None
        description = request.form['description']

        # Calculate the new paid_until date
        if paid_duration > 0:
            paid_until = (datetime.now() + timedelta(days=30 * paid_duration)).strftime('%Y-%m-%d')

        # Validate role
        if role not in ['User', 'Passiv', 'Manager', 'Vorstand']:
            flash("Invalid role specified. Please select a valid role.", 'error')
            return redirect(url_for('users.users'))

        # Database operations
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        try:
            if user_id:  # Update existing user
                if password:  # Update password if provided
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    c.execute("""
                        UPDATE users SET name = ?, nickname = ?, phone = ?, email = ?, password = ?, role = ?, 
                        show_email = ?, show_phone = ?, has_key = ?, paid = ?, street = ?, number = ?, city = ?, 
                        postcode = ?, birthday = ?, patron = ?, patron_amount = ?, paid_until = ?, member_since = ?, 
                        show_birthday = ?, description = ? WHERE id = ?
                    """, (name, nickname, phone, email, hashed_password, role, show_email, show_phone, has_key, 
                        paid, street, number, city, postcode, birthday, patron, patron_amount, paid_until, 
                        member_since, show_birthday, description, user_id))
                else:  # Update without changing the password
                    c.execute("""
                        UPDATE users SET name = ?, nickname = ?, phone = ?, email = ?, role = ?, 
                        show_email = ?, show_phone = ?, has_key = ?, paid = ?, street = ?, number = ?, city = ?, 
                        postcode = ?, birthday = ?, patron = ?, patron_amount = ?, paid_until = ?, member_since = ?, 
                        show_birthday = ?, description = ? WHERE id = ?
                    """, (name, nickname, phone, email, role, show_email, show_phone, has_key, paid, street, number, city,
                        postcode, birthday, patron, patron_amount, paid_until, member_since, show_birthday, description, user_id))
            else:  # Add new user
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                c.execute("""
                    INSERT INTO users (name, nickname, phone, email, password, role, show_email, show_phone, 
                    has_key, paid, street, number, city, postcode, birthday, patron, patron_amount, paid_until, 
                    member_since, show_birthday, description) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, nickname, phone, email, hashed_password, role, show_email, show_phone, has_key, 
                    paid, street, number, city, postcode, birthday, patron, patron_amount, paid_until, 
                    member_since, show_birthday, description))

            conn.commit()


        except sqlite3.Error as e:
            flash(f"Error saving user: {e}", 'error')

        finally:
            conn.close()

        flash('User saved successfully!', 'success')
        return redirect(url_for('users.users'))

    # Render template with user data
    return render_template(
        'users.html', 
        users=users, 
        active_page='Mitglieder', 
        title='Mitglieder'
    )

# Delete user route
@users_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'logged_in' not in session or not session['logged_in'] or session['role'] not in ['Admin', 'Vorstand']:
        return redirect(url_for('login.login'))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        flash(f"Error deleting user: {e}", 'error')
    finally:
        conn.close()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('users.users'))

# Get user details for edit route
@users_bp.route('/get_user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if 'logged_in' not in session or not session['logged_in'] or session['role'] not in ['Admin', 'Vorstand']:
        return redirect(url_for('login.login'))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, name, nickname, phone, email, role, show_email, show_phone, has_key, paid, 
                 street, number, city, postcode, birthday, patron, patron_amount, paid_until, member_since, show_birthday, 
                 description 
                 FROM users WHERE id = ?""", (user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        user_data = {
            "id": user[0],
            "name": user[1],
            "nickname": user[2],
            "phone": user[3],
            "email": user[4],
            "role": user[5],
            "show_email": bool(user[6]),
            "show_phone": bool(user[7]),
            "has_key": bool(user[8]),
            "paid": bool(user[9]),
            "street": user[10],
            "number": user[11],
            "city": user[12],
            "postcode": user[13],
            "birthday": user[14],
            "patron": bool(user[15]),
            "patron_amount": user[16],
            "paid_until": user[17],
            "member_since": user[18],
            "show_birthday": bool(user[19]),
            "description": user[20]
        }
        return jsonify(user_data)
    return jsonify({"error": "User not found"}), 404


print(users)