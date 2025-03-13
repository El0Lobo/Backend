import jwt
import time
import random
import sqlite3
import bcrypt
from functools import wraps
from flask import request, redirect, url_for, jsonify, session

# JWT configuration
JWT_KEY = "YOUR_SECRET_KEY"
JWT_ALGO = "HS256"
JWT_ISS = "Backend"

# Database file and folder for JSON data
DB_FILE = 'database.db'
JSON_FOLDER = 'json_data'

#############################
# JWT Utility Functions
#############################

def jwtSign(email, name, role):
    """
    Generate a JWT token with a random JWT ID and a 1-hour expiration.
    """
    rnd = "".join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz~!@#$%^_-") for i in range(24))
    now = int(time.time())
    payload = {
        "iat": now,            # Issued at time
        "nbf": now,            # Not valid before this time
        "exp": now + 3600,     # Expires in 1 hour
        "jti": rnd,            # JWT ID (random string)
        "iss": JWT_ISS,        # Issuer
        "data": {"email": email, "name": name, "role": role}
    }
    return jwt.encode(payload, JWT_KEY, algorithm=JWT_ALGO)

def jwtVerify(cookies):
    """
    Verify the JWT token present in the cookies.
    Returns the user data if the token is valid, otherwise returns False.
    """
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

def role_required(required_roles):
    """
    Decorator that checks if the current user's role is in the required_roles list.
    If not, it redirects the user to the login page.
    """
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
    """
    Retrieve a user's details from the database by their email address.
    Returns a dictionary of user details or None if the user is not found.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Allow access by column name
    c = conn.cursor()
    c.execute("SELECT id, name, nickname, email, password, role FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            "id": user["id"],
            "name": user["name"],
            "nickname": user["nickname"],
            "email": user["email"],
            "password": user["password"],  # Note: This is the hashed password.
            "role": user["role"]
        }
    return None

##################################
# Database Initialization Function
##################################

def init_db():
    conn = None
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Create the users table
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

        # Create the news table
        c.execute('''CREATE TABLE IF NOT EXISTS news (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        description TEXT,
                        date TEXT,
                        image_path TEXT,
                        intern BOOLEAN
                    )''')
        
        # Create the events table
        c.execute('''CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        date TEXT,
                        type TEXT NOT NULL,
                        entry_time TEXT,
                        end_time TEXT,
                        price REAL DEFAULT 0,
                        location TEXT DEFAULT '',
                        num_people_per_shift INTEGER DEFAULT 1,
                        theke_shift BOOLEAN DEFAULT 0,
                        door_shift BOOLEAN DEFAULT 0,
                        double_shift BOOLEAN DEFAULT 0,
                        weekly BOOLEAN DEFAULT 0,
                        monthly BOOLEAN DEFAULT 0,
                        intern BOOLEAN DEFAULT 0,
                        proposed BOOLEAN DEFAULT 0,
                        closed_from TEXT,
                        closed_to TEXT,
                        konzertstart TEXT,
                        image_path TEXT,
                        replace_event BOOLEAN DEFAULT 0,
                        intern_event_type TEXT NOT NULL
                    )''')
        
        # Create the bands table
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
        
        # Create the stuff table
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
        
        # Create the votes table
        c.execute('''CREATE TABLE IF NOT EXISTS votes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        options TEXT NOT NULL,
                        eligible_roles TEXT NOT NULL,
                        multiple_choice BOOLEAN NOT NULL DEFAULT 0,
                        max_votes INTEGER DEFAULT 1,
                        voting_finished BOOLEAN NOT NULL DEFAULT 0
                     )''')
        
        # Create the user_votes table
        c.execute('''CREATE TABLE IF NOT EXISTS user_votes (
                        vote_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        choices TEXT NOT NULL,
                        PRIMARY KEY (vote_id, user_id),
                        FOREIGN KEY (vote_id) REFERENCES votes(id) ON DELETE CASCADE
                    )''')
        
        # Create the contacts table
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
        
        # Create the shift_assignments table
        c.execute('''CREATE TABLE IF NOT EXISTS shift_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL,
                        shift_type TEXT NOT NULL,
                        schicht INTEGER NOT NULL,
                        shift_index INTEGER NOT NULL,
                        user_nick TEXT NOT NULL,
                        date TEXT NOT NULL,
                        FOREIGN KEY(event_id) REFERENCES events(id)
                    )''')
        
        # Create the guests table
        c.execute('''CREATE TABLE IF NOT EXISTS guests (
                        name TEXT,
                        annotation TEXT,
                        date TEXT,
                        PRIMARY KEY (name, date)
                    )''')

        # Create the banned table
        c.execute('''CREATE TABLE IF NOT EXISTS banned (
                        name TEXT PRIMARY KEY,
                        reason TEXT,
                        description TEXT,
                        social_link TEXT,
                        date TEXT,
                        ban_until TEXT
                    )''')

        # Create the banned_suggestions table
        c.execute('''CREATE TABLE IF NOT EXISTS banned_suggestions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        reason TEXT,
                        description TEXT,
                        social_link TEXT,
                        date TEXT,
                        ban_until TEXT,
                        submitted_by TEXT
                    )''')

        c.execute('''CREATE TABLE IF NOT EXISTS stuff_to_sell (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,  -- JSON string containing detailed item information
                        image_path TEXT,
                        date_added TEXT NOT NULL,
                        user_name TEXT NOT NULL,
                        is_intern BOOLEAN NOT NULL DEFAULT 0
                    )''')


        # Insert default admin users if they do not exist.
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

        # Commit all changes to the database.
        conn.commit()
        print("Database initialized successfully.")

    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")

    finally:
        # Ensure the database connection is closed.
        if conn:
            conn.close()
