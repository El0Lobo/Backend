from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, jsonify

import sqlite3
import bcrypt
from routes.utils import jwtSign, jwtVerify, getUserByEmail  # Import necessary functions from utils.py


login_bp = Blueprint('login', __name__)

DB_FILE = 'database.db'

# LOGIN PAGE ENDPOINT
@login_bp.route('/login', methods=['GET'])
def login():
    if jwtVerify(request.cookies):  # Verify JWT from cookies to check if already logged in
        return redirect(url_for('news.news'))  # Redirect to news page if logged in
    else:
        return render_template('login.html')  # Render login page

# LOGIN ACTION ENDPOINT (SIMILAR TO YOUR /in)
@login_bp.route('/in', methods=['POST'])
def lin():
    data = dict(request.form)
    user = getUserByEmail(data["email"])

    # Debugging: Print the retrieved hashed password
    if user:
        print("Retrieved password hash from database:", user["password"])  # Print to confirm the format
        # Example of a hardcoded bcrypt check to isolate issue
        test_password = "Abandonallhope,yewhoenterhere"
        test_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        print("Example hashed password for comparison:", test_hash)
        # Try a bcrypt check with the actual data
        try:
            print("Checking bcrypt with retrieved hash...")
            valid = bcrypt.checkpw(data["password"].encode('utf-8'), user["password"].encode('utf-8'))
        except ValueError as e:
            print("Error during bcrypt check:", e)  # Print the error for debugging
            flash("There was an issue with password validation.", 'error')
            return redirect(url_for('login.login'))
    else:
        flash("Invalid email/password", 'error')
        return redirect(url_for('login.login'))
    
    if valid:
        # Set session values for logged in user
        session['logged_in'] = True
        session['name'] = user["name"]
        session['nickname'] = user["nickname"]  # Add the nickname to the session
        session['role'] = user["role"]

        # If valid credentials, create JWT and set it in cookies
        token = jwtSign(data["email"], user["name"], user["role"])  # Include name
        res = make_response(redirect(url_for('news.news')))
        res.set_cookie('JWT', token)
        return res

    else:
        flash("Invalid email/password", 'error')
        return redirect(url_for('login.login'))


# LOGOUT ENDPOINT (SIMILAR TO YOUR /out)
@login_bp.route('/out', methods=['POST'])
def lout():
    # Clear the session data and JWT cookie
    session.clear()
    res = make_response(redirect(url_for('login.login')))
    res.delete_cookie('JWT')  # Clear JWT by deleting the cookie
    return res

@login_bp.route('/api/session/nickname', methods=['GET'])
def get_nickname():
    if 'logged_in' in session and session['logged_in']:
        nickname = session.get('nickname')
        if nickname:
            return jsonify({"nickname": nickname})
        else:
            return jsonify({"nickname": "Unknown"})  # Ensure "Unknown" is a fallback
    else:
        return jsonify({"error": "Not logged in"}), 401