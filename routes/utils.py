import jwt
import time
import random
import sqlite3
import bcrypt
from functools import wraps
from flask import request, redirect, url_for

JWT_KEY = "YOUR_SECRET_KEY"
JWT_ALGO = "HS256"
JWT_ISS = "Backend"

DB_FILE = 'database.db'
JSON_FOLDER = 'json_data'

# Generate JWT Token
def jwtSign(email, name, role):
    rnd = "".join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz~!@#$%^_-") for i in range(24))
    now = int(time.time())
    return jwt.encode({
        "iat": now,  # Issued at
        "nbf": now,  # Not before
        "exp": now + 3600,  # Expiry time (1 hour)
        "jti": rnd,  # Random JWT ID
        "iss": JWT_ISS,  # Issuer
        "data": {"email": email, "name": name, "role": role}
    }, JWT_KEY, algorithm=JWT_ALGO)

# Verify JWT Token
def jwtVerify(cookies):
    try:
        jwt_token = cookies.get("JWT")
        if jwt_token is None:
            return False

        user = jwt.decode(jwt_token, JWT_KEY, algorithms=[JWT_ALGO])
        return user["data"]
    except jwt.ExpiredSignatureError:
        print("Token expired.")
        return False
    except jwt.InvalidTokenError:
        print("Invalid token.")
        return False

# Role-based Access Decorator
def role_required(required_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            user = jwtVerify(request.cookies)
            if not user or user.get("role") not in required_roles:
                return redirect(url_for("login.login"))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def getUserByEmail(email):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows dictionary-style access to rows
    c = conn.cursor()
    c.execute("SELECT id, name, nickname, email, password, role FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            "id": user["id"],
            "name": user["name"],
            "nickname": user["nickname"],  # Include nickname
            "email": user["email"],
            "password": user["password"],  # Ensure this retrieves the hashed password
            "role": user["role"]
        }
    return None


# Initialize Database
def init_db():
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Create users table without CHECK constraint for testing
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        nickname TEXT,
                        email TEXT UNIQUE NOT NULL,
                        phone TEXT,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        show_email INTEGER DEFAULT 0,
                        show_phone INTEGER DEFAULT 0,
                        has_key INTEGER DEFAULT 0,
                        paid INTEGER DEFAULT 0,
                        street TEXT,
                        number INTEGER,
                        city TEXT,
                        postcode TEXT,
                        birthday DATE,
                        patron INTEGER DEFAULT 0,              
                        patron_amount REAL DEFAULT 0.0,
                        paid_until DATE DEFAULT NULL,
                        member_since DATE DEFAULT NULL,       
                        show_birthday INTEGER DEFAULT 0,
                        description TEXT      
                    )''')

        c.execute('''CREATE TABLE IF NOT EXISTS news (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        description TEXT,
                        date TEXT,
                        image_path TEXT,
                        intern BOOLEAN
                    )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        date TEXT, -- ISO 8601 format (YYYY-MM-DD)
                        type TEXT NOT NULL, -- Matches Schema.org types (e.g., MusicEvent, DJEvent)
                        entry_time TEXT, -- Time (HH:MM)
                        end_time TEXT, -- Time (HH:MM) for event end
                        price REAL DEFAULT 0, -- Event price in Euros
                        location TEXT DEFAULT '', -- Event location or venue
                        num_people_per_shift INTEGER DEFAULT 1, -- Number of people required per shift
                        theke_shift BOOLEAN DEFAULT 0, -- Whether bar shift is needed
                        door_shift BOOLEAN DEFAULT 0, -- Whether door shift is needed
                        double_shift BOOLEAN DEFAULT 0, -- Whether double shifts are enabled
                        weekly BOOLEAN DEFAULT 0, -- Weekly recurrence
                        monthly BOOLEAN DEFAULT 0, -- Monthly recurrence
                        intern BOOLEAN DEFAULT 0, -- Internal event
                        proposed BOOLEAN DEFAULT 0, -- Proposed event
                        closed_from TEXT, -- Start date for holiday breaks (ISO 8601 format)
                        closed_to TEXT, -- End date for holiday breaks (ISO 8601 format)
                        konzertstart TEXT, -- Time (HH:MM) for concert start
                        image_path TEXT, -- Path to event image
                        replace_event BOOLEAN DEFAULT 0, -- Whether the event replaces another event
                        intern_event_type TEXT NOT NULL -- For Internal Use
                    )''')

        c.execute('''CREATE TABLE IF NOT EXISTS bands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        logo TEXT,
                        genre TEXT,
                        bandcamp TEXT,
                        facebook TEXT,
                        instagram TEXT,
                        youtube TEXT,
                        contact_method TEXT,
                        last_booked TEXT,
                        comments TEXT,
                        type TEXT NOT NULL CHECK(type IN ('Band', 'DJ')),
                        doordeal BOOLEAN DEFAULT 0,
                        price REAL
                     )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS stuff (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        image_path TEXT,
                        date_added TEXT NOT NULL,
                        bought BOOLEAN NOT NULL DEFAULT 0,
                        user_name TEXT NOT NULL,
                        is_intern BOOLEAN NOT NULL DEFAULT 0
                     )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS votes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        options TEXT NOT NULL,
                        eligible_roles TEXT NOT NULL,
                        multiple_choice BOOLEAN NOT NULL DEFAULT 0,
                        max_votes INTEGER DEFAULT 1,
                        voting_finished BOOLEAN NOT NULL DEFAULT 0
                     )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_votes (
                        vote_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        choices TEXT NOT NULL,
                        PRIMARY KEY (vote_id, user_id),
                        FOREIGN KEY (vote_id) REFERENCES votes(id) ON DELETE CASCADE
                    )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        name TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        details TEXT,
                        username TEXT,
                        password TEXT,
                        url TEXT,
                        notes TEXT
                     )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS shift_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL,
                        shift_type TEXT NOT NULL,
                        schicht INTEGER NOT NULL,
                        shift_index INTEGER NOT NULL, -- Renamed from 'index'
                        user_nick TEXT NOT NULL,
                        date TEXT NOT NULL,
                        FOREIGN KEY(event_id) REFERENCES events(id)
                    )''')

        # Add default admin users if they do not exist
        admins = [
            ('Admin', 'Admin', 'admin@contrast.com', 'Abandonallhope,yewhoenterhere', 'Admin'),
            ('Lobo', 'Lobo', 'lobo@contrast.com', 'alwaysseeyourface', 'Admin')
        ]

        for name, nickname, email, password, role in admins:
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            if not c.fetchone():
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                c.execute("INSERT INTO users (name, nickname, email, password, role) VALUES (?, ?, ?, ?, ?)",
                        (name, nickname, email, hashed_password, role))

        # Commit changes
        conn.commit()
        print("Database initialized successfully.")

    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")

    finally:
        # Make sure to close the connection properly
        if conn:
            conn.close()
