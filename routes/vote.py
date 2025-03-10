from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
import sqlite3
import json
from routes.utils import jwtVerify

vote_bp = Blueprint('vote', __name__)
DB_FILE = 'database.db'

# Function to load vote details
def load_vote(vote_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM votes WHERE id = ?", (vote_id,))
    vote = c.fetchone()
    conn.close()
    if vote:
        return {
            "id": vote[0],
            "title": vote[1],
            "options": json.loads(vote[2]),  # JSON string to dictionary
            "eligible_roles": json.loads(vote[3]),  # JSON array of roles
            "multiple_choice": bool(vote[4]),
            "max_votes": vote[5],
            "voting_finished": bool(vote[6])
        }
    return None

@vote_bp.route('/vote', methods=['GET', 'POST'])
def vote():
    user = jwtVerify(request.cookies) or session  # Using role directly
    user_role = user.get("role")

    if not user_role:
        return jsonify({"error": "Unauthorized"}), 403

    # Handle POST request for voting
    if request.method == 'POST':
        vote_id = request.form['vote_id']
        selected_options = request.form.getlist('selected_options')

        # Load vote and verify eligibility
        vote = load_vote(vote_id)
        if not vote or (user_role not in vote['eligible_roles'] and user_role not in ['Admin', 'Vorstand']) or vote['voting_finished']:
            return jsonify({"error": "Unauthorized or voting ended"}), 403
        
        if len(selected_options) > vote['max_votes']:
            return jsonify({"error": f"You can select up to {vote['max_votes']} options."}), 400

        # Update vote counts
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        options = vote['options']
        for option in selected_options:
            options[option] += 1
        c.execute("UPDATE votes SET options = ? WHERE id = ?", (json.dumps(options), vote_id))
        conn.commit()
        conn.close()

        # Redirect back to the vote page to reload votes
        return redirect(url_for('vote.vote'))

    # Fetch active and decided votes for display
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM votes WHERE voting_finished = 0")
    active_votes = [load_vote(row[0]) for row in c.fetchall()]
    c.execute("SELECT * FROM votes WHERE voting_finished = 1")
    decided_votes = [load_vote(row[0]) for row in c.fetchall()]
    conn.close()

    return render_template('vote.html', user=user, active_votes=active_votes, decided_votes=decided_votes, active_page='Vote', title='Vote')

@vote_bp.route('/vote/finish/<int:vote_id>', methods=['POST'])
def finish_vote(vote_id):
    user = jwtVerify(request.cookies)
    user_role = user.get("role")

    if user_role not in ['Admin', 'Vorstand']:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE votes SET voting_finished = 1 WHERE id = ?", (vote_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Vote marked as decided"}), 200

@vote_bp.route('/vote/create', methods=['POST'])
def create_vote():
    user = jwtVerify(request.cookies)
    user_role = user.get("role")

    if user_role not in ['Admin', 'Vorstand']:
        return jsonify({"error": "Unauthorized"}), 403

    title = request.form.get('title')
    description = request.form.get('description')
    eligible_roles = request.form.get('eligible_roles')
    multiple_choice = bool(request.form.get('multiple_choice'))
    num_options = int(request.form.get('num_options', 1))

    # Collect options from dynamically generated fields
    options = {}
    for i in range(1, num_options + 1):
        option = request.form.get(f'option_{i}')
        if option:
            options[option] = 0  # Initialize vote count to 0 for each option

    # Save the new vote to the database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO votes (title, options, eligible_roles, multiple_choice, max_votes, voting_finished)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (title, json.dumps(options), json.dumps([eligible_roles]), multiple_choice, num_options))
    conn.commit()
    conn.close()
    
    return redirect(url_for('vote.vote'))
