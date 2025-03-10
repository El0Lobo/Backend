from flask import Flask
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from routes.login import login_bp
from routes.news import news_bp
from routes.events import events_bp
from routes.utils import jwtSign, jwtVerify, init_db
from routes.setup import setup_bp
from routes.users import users_bp
from routes.bands import bands_bp
from routes.stuff import stuff_bp
from routes.vote import vote_bp
from routes.contact import contact_bp
""" from routes.door import door_bp """

# Flask App Setup
app = Flask(__name__)

# Register Blueprints
app.register_blueprint(login_bp)
app.register_blueprint(news_bp)
app.register_blueprint(events_bp)
app.register_blueprint(users_bp)
app.register_blueprint(setup_bp)
app.register_blueprint(bands_bp)
app.register_blueprint(stuff_bp)
app.register_blueprint(vote_bp)
app.register_blueprint(contact_bp)
""" app.register_blueprint(door_bp) """

# Secret keys for JWT and session
app.secret_key = 'YOUR_SECRET_KEY'
JWT_SECRET = "YOUR_SECRET_KEY"
JWT_ALGO = "HS256"

# Upload folder setup
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Setup
DB_FILE = 'database.db'

# Initialize the Database and Confirm
print("Initializing the database...")
init_db()
print("Database initialized successfully.")

# Define the custom filter for German date formatting
def format_date_german(date_string):
    date_obj = datetime.strptime(date_string, "%Y-%m-%d")
    return date_obj.strftime("%d.%m.%Y")

# Register the filter with Jinja2
app.jinja_env.filters['german_date'] = format_date_german

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
