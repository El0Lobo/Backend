from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
import sqlite3
import json
from datetime import datetime
from routes.utils import jwtVerify

door_bp = Blueprint('door', __name__)
DB_FILE = 'database.db'

def today_date():
    return datetime.now().strftime("%d-%m-%Y")

# ---------------- Guest List Endpoints ----------------

def get_guests(date_str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, annotation FROM guests WHERE date = ?", (date_str,))
    guests = [{"name": row[0], "annotation": row[1]} for row in c.fetchall()]
    conn.close()
    return guests

@door_bp.route('/door', methods=['GET'])
def door():
    user = jwtVerify(request.cookies) or session
    if not user.get("role"):
        return jsonify({"error": "Unauthorized"}), 403

    # Use query parameter "date" or default to today
    date_str = request.args.get("date") or today_date()
    guests = get_guests(date_str)

    # Fetch banned list with the new ban_until and description fields
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, reason, social_link, date, ban_until, description FROM banned")
    banned = [{
        "name": row[0],
        "reason": row[1],
        "social_link": row[2],
        "date": row[3],
        "ban_until": row[4],
        "description": row[5]
    } for row in c.fetchall()]
    conn.close()

    # If user is admin or vorstand, also fetch banned suggestions with the new fields
    banned_suggestions = []
    if user.get("role").lower() in ['admin', 'vorstand']:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name, reason, social_link, date, submitted_by, ban_until, description FROM banned_suggestions")
        banned_suggestions = [{
            "id": row[0],
            "name": row[1],
            "reason": row[2],
            "social_link": row[3],
            "date": row[4],
            "submitted_by": row[5],
            "ban_until": row[6],
            "description": row[7]
        } for row in c.fetchall()]
        conn.close()

    return render_template('door.html',
                           user=user,
                           guest_data=guests,
                           banned_data=banned,
                           banned_suggestions=banned_suggestions,
                           selected_date=date_str)

@door_bp.route('/add_guest', methods=['POST'])
def add_guest():
    user = jwtVerify(request.cookies) or session
    # For guests, admins, vorstand, and managers can add directly
    if user.get("role").lower() not in ['admin', 'vorstand', 'manager']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json()
    name = data.get("name")
    annotation = data.get("annotation")
    date_str = data.get("date") or today_date()
    if not name or not annotation:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO guests (name, annotation, date) VALUES (?, ?, ?)", (name, annotation, date_str))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "message": "Guest already exists for that date"}), 400
    conn.close()
    return jsonify({"success": True, "message": "Guest added", "date": date_str})

@door_bp.route('/remove_guest/<name>/<date_str>', methods=['DELETE'])
def remove_guest(name, date_str):
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM guests WHERE name = ? AND date = ?", (name, date_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Guest {name} removed from {date_str}"})

@door_bp.route('/clear_guest_list', methods=['DELETE'])
def clear_guest_list():
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json()
    date_str = data.get("date") or today_date()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM guests WHERE date = ?", (date_str,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Guest list cleared for {date_str}"})

@door_bp.route('/edit_guest', methods=['POST'])
def edit_guest():
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json()
    old_name = data.get("old_name")
    date_str = data.get("date")
    new_name = data.get("new_name")
    new_annotation = data.get("new_annotation")
    if not old_name or not new_name or not new_annotation or not date_str:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE guests SET name = ?, annotation = ? WHERE name = ? AND date = ?",
              (new_name, new_annotation, old_name, date_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Guest updated"})

# ---------------- Banned List Endpoints ----------------

@door_bp.route('/add_banned', methods=['POST'])
def add_banned():
    user = jwtVerify(request.cookies) or session
    data = request.get_json()
    name = data.get("name")
    reason = data.get("reason")
    description = data.get("description")  # description field (backend name)
    social_link = data.get("social_link")
    date_str = data.get("date") or today_date()
    ban_until = data.get("ban_until")  # new field for ban duration

    if not name or not reason:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if user.get("role").lower() in ['admin', 'vorstand']:
        try:
            c.execute("INSERT INTO banned (name, reason, description, social_link, date, ban_until) VALUES (?, ?, ?, ?, ?, ?)",
                      (name, reason, description, social_link, date_str, ban_until))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"success": False, "message": "This person is already banned"}), 400
        conn.close()
        return jsonify({"success": True, "message": "Banned person added", "date": date_str})
    else:
        submitted_by = user.get("username", "unknown")
        c.execute("INSERT INTO banned_suggestions (name, reason, description, social_link, date, submitted_by, ban_until) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (name, reason, description, social_link, date_str, submitted_by, ban_until))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Banned person suggestion submitted", "date": date_str})

@door_bp.route('/remove_banned/<name>', methods=['DELETE'])
def remove_banned(name):
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM banned WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Banned person {name} removed"})

@door_bp.route('/edit_banned', methods=['POST'])
def edit_banned():
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json()
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    new_reason = data.get("new_reason")
    new_description = data.get("new_description")  # new_description field
    new_social_link = data.get("new_social_link")
    new_date = data.get("new_date")
    new_ban_until = data.get("new_ban_until")  # new ban duration

    if not old_name or not new_name or not new_reason or not new_date:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE banned SET name = ?, reason = ?, description = ?, social_link = ?, date = ?, ban_until = ? WHERE name = ?",
              (new_name, new_reason, new_description, new_social_link, new_date, new_ban_until, old_name))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Banned entry updated"})

@door_bp.route('/banned_suggestions', methods=['GET'])
def view_banned_suggestions():
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, reason, social_link, date, submitted_by FROM banned_suggestions")
    suggestions = [{
        "id": row[0],
        "name": row[1],
        "reason": row[2],
        "social_link": row[3],
        "date": row[4],
        "submitted_by": row[5]
    } for row in c.fetchall()]
    conn.close()
    return jsonify({"suggestions": suggestions})

@door_bp.route('/approve_banned/<int:suggestion_id>', methods=['POST'])
def approve_banned(suggestion_id):
    user = jwtVerify(request.cookies) or session
    if user.get("role").lower() not in ['admin', 'vorstand']:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Now include ban_until and description in the selection
    c.execute("SELECT name, reason, social_link, date, ban_until, description FROM banned_suggestions WHERE id = ?", (suggestion_id,))
    suggestion = c.fetchone()
    if not suggestion:
        conn.close()
        return jsonify({"error": "Suggestion not found"}), 404

    name, reason, social_link, date_str, ban_until, description = suggestion
    try:
        c.execute("INSERT INTO banned (name, reason, description, social_link, date, ban_until) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, reason, description, social_link, date_str, ban_until))
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "This person is already banned"}), 400

    c.execute("DELETE FROM banned_suggestions WHERE id = ?", (suggestion_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Banned person approved and added"})

