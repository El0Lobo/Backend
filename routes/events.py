import os
import sqlite3
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

# Initialize logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

events_bp = Blueprint('events', __name__)

DB_FILE = 'database.db'

# Helper function to connect to the database
def connect_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# Route to display events
# Helper function to categorize events
def categorize_events(events):
    current_date = datetime.now().date()
    for event in events:
        # Check if the event is in the past
        event["in_past"] = datetime.strptime(event["date"], "%Y-%m-%d").date() < current_date
        # Check if the event is proposed/suggested
        event["suggested"] = event.get("proposed", 0) == 1
    return events


# Route to display events
@events_bp.route('/events', methods=['GET'])
def events():
    logger.debug("Fetching events for rendering...")
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM events ORDER BY date ASC")
    events = c.fetchall()
    conn.close()

    # Convert events to dicts and categorize them
    all_events = categorize_events([dict(event) for event in events])
    logger.debug(f"Fetched events: {all_events}")

    return render_template('calendar.html', events=all_events)


# Route to add an event
@events_bp.route('/add_event', methods=['POST'])
def add_event():
    try:
        from werkzeug.utils import secure_filename
        import os

        logger.debug("Starting to process the add_event request...")

        UPLOAD_FOLDER = os.path.join('static', 'uploads')
        ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        # Ensure upload folder exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Capture form data and file upload
        data = request.form
        file = request.files.get('event_image')
        logger.debug(f"Form data received: {data}")
        logger.debug(f"Request files: {request.files}")

        # Extract and validate form fields
        name = data.get('event_name')
        description = data.get('description')
        date = data.get('event_date')
        event_type = data.get('schema_type')
        entry_time = data.get('einlasszeit')
        end_time = data.get('end')
        price = data.get('price', '0').strip()
        price = float(price) if price else 0.0
        location = data.get('location', '')
        num_people_per_shift = int(data.get('num_people_per_shift', 1))
        theke_shift = int(data.get('theke_shift') == 'on')
        door_shift = int(data.get('door_shift') == 'on')
        double_shift = int(data.get('double_shift') == 'on')
        weekly = int(data.get('weekly') == 'on')
        monthly = int(data.get('monthly') == 'on')
        intern = int(data.get('intern') == 'on')
        proposed = int(data.get('proposed') == 'on')
        closed_from = data.get('closed_from') or None
        closed_to = data.get('closed_to') or None
        konzertstart = data.get('konzertstart') or None
        replace_event = int(data.get('replace') == 'on')
        intern_event_type = data.get('intern_event_type', 'General')

        logger.debug(f"Parsed form data: name={name}, date={date}, type={event_type}")

        # Check for required fields
        if not name or not date:
            flash('Event name and date are required!', 'error')
            logger.error("Validation failed: Missing required fields (name or date).")
            return redirect(url_for('events.events'))

        # Handle image upload
        image_path = None
        if file:
            if allowed_file(file.filename):
                filename = secure_filename(f"{name.replace(' ', '_').lower()}-event.jpg")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_path = filename
                logger.info(f"Image uploaded successfully: {filename}")
            else:
                flash("Invalid file type. Only JPG, PNG, and GIF are allowed.", "error")
                logger.error(f"Invalid file type for {file.filename}")
                return redirect(url_for('events.events'))
        else:
            logger.info("No file uploaded.")

        # Insert event into the database
        conn = connect_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO events (
                name, description, date, type, entry_time, end_time, price, location,
                num_people_per_shift, theke_shift, door_shift, double_shift,
                weekly, monthly, intern, closed_from, closed_to, konzertstart, 
                proposed, replace_event, image_path, intern_event_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, description, date, event_type, entry_time, end_time, price, location,
            num_people_per_shift, theke_shift, door_shift, double_shift,
            weekly, monthly, intern, closed_from, closed_to, konzertstart, 
            proposed, replace_event, image_path, intern_event_type
        ))
        conn.commit()
        logger.info("Event added to the database successfully.")
        conn.close()

        flash('Event added successfully!')
        return redirect(url_for('events.events'))

    except sqlite3.Error as sql_error:
        logger.error(f"Database error occurred: {sql_error}")
        flash("Database error occurred while adding the event.", "error")
        return redirect(url_for('events.events'))

    except Exception as e:
        logger.error(f"Error in /add_event route: {e}")
        flash("An error occurred while adding the event. Please try again.", "error")
        return redirect(url_for('events.events'))


# API to fetch all events
@events_bp.route('/api/events', methods=['GET'])
def api_events():
    try:
        conn = connect_db()
        c = conn.cursor()

        # Fetch all events
        c.execute("SELECT * FROM events")
        events = c.fetchall()

        # Fetch all shift assignments
        c.execute("SELECT * FROM shift_assignments")
        shift_assignments = c.fetchall()
        conn.close()

        # Map shift assignments by event_id
        assignments_by_event = {}
        for assignment in shift_assignments:
            event_id = assignment["event_id"]
            if event_id not in assignments_by_event:
                assignments_by_event[event_id] = []
            assignments_by_event[event_id].append({
                "shift_type": assignment["shift_type"],
                "schicht": assignment["schicht"],
                "shift_index": assignment["shift_index"],
                "user_nick": assignment["user_nick"],
            })

        # Add assignments to events
        response = []
        for event in events:
            event_dict = dict(event)
            event_dict["assignments"] = assignments_by_event.get(event["id"], [])
            response.append(event_dict)

        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in /api/events route: {e}")
        return jsonify([]), 500

# Handle recurring events
def handle_recurring_events(events):
    recurring_events = []
    today = datetime.today().date()
    future_limit = today + timedelta(days=365)  # Process events for the next year

    for event in events:
        if event["weekly"]:  # Handle weekly recurrence
            start_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
            current_date = start_date

            while current_date <= future_limit:
                if current_date.weekday() == start_date.weekday():  # Match the day of the week
                    recurring_events.append({
                        "id": event["id"],
                        "name": event["name"],
                        "description": event["description"],
                        "date": current_date.isoformat(),
                        "type": event["type"],
                    })
                current_date += timedelta(weeks=1)

        if event["monthly"]:  # Handle monthly recurrence
            start_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
            current_date = start_date

            while current_date <= future_limit:
                recurring_events.append({
                    "id": event["id"],
                    "name": event["name"],
                    "description": event["description"],
                    "date": current_date.isoformat(),
                    "type": event["type"],
                })
                current_date += relativedelta(months=1)

    logger.debug(f"Recurring events: {recurring_events}")
    return recurring_events

@events_bp.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()

        flash('Event deleted successfully!', 'success')
        logger.info(f"Event with ID {event_id} deleted successfully.")
        return redirect(url_for('events.events'))
    except sqlite3.Error as e:
        logger.error(f"Error deleting event: {e}")
        flash('An error occurred while deleting the event.', 'error')
        return redirect(url_for('events.events'))

@events_bp.route('/api/users', methods=['GET'])
def get_users():
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT nickname, role FROM users")
        users = c.fetchall()
        conn.close()
        return jsonify([dict(user) for user in users])
    except Exception as e:
        logger.error(f"Error in /api/users route: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@events_bp.route('/api/session/role', methods=['GET'])
def get_session_role():
    """
    Provide the role of the currently logged-in user.
    Assumes role is stored in session during authentication.
    """
    role = session.get('role')  # Ensure role is set during user login
    if role:
        return jsonify({"role": role}), 200
    return jsonify({"error": "Role not found"}), 404


@events_bp.route('/api/shifts', methods=['POST'])
def assign_shift():
    data = request.json
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO shift_assignments (
                event_id, shift_type, schicht, shift_index, user_nick, date
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['event_id'], data['shift_type'], data['schicht'], data['shift_index'], data['user_nick'], data['date']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Shift assigned'}), 201
    except sqlite3.Error as e:
        logger.error(f"Database error in assign_shift: {e}")
        return jsonify({'error': 'Database error'}), 500


@events_bp.route('/api/shifts', methods=['DELETE'])
def unassign_shift():
    data = request.json
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('''
            DELETE FROM shift_assignments 
            WHERE event_id = ? AND shift_type = ? AND schicht = ? AND shift_index = ? AND date = ?
        ''', (data['event_id'], data['shift_type'], data['schicht'], data['shift_index'], data['date']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Shift unassigned'}), 200
    except sqlite3.Error as e:
        logger.error(f"Database error in unassign_shift: {e}")
        return jsonify({'error': 'Database error'}), 500


@events_bp.route('/api/shifts/<int:event_id>/<shift_type>/<int:schicht>/<int:index>', methods=['GET'])
def get_shift(event_id, shift_type, schicht, index):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('''
            SELECT user_nick FROM shift_assignments
            WHERE event_id = ? AND shift_type = ? AND schicht = ? AND shift_index = ? AND date = ?
        ''', (event_id, shift_type, schicht, index, datetime.now().strftime('%Y-%m-%d')))
        assignment = c.fetchone()
        conn.close()

        if assignment:
            return jsonify({'user_nick': assignment['user_nick']})
        return jsonify({'user_nick': None}), 200
    except Exception as e:
        logger.error(f"Error fetching shift: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500
