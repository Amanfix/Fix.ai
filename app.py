import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
import openai

load_dotenv() # Load environment variables from .env file

# App initialization
app = Flask(__name__)

# Configurations
app.config['SECRET_KEY'] = 'a_very_secret_key' # Replace with a real secret key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # The route to redirect to if user is not logged in
CORS(app) # Keeping CORS for the API endpoint, though session-based auth is primary now

# User model for the database
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat_page'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('chat_page'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'warning')
            return redirect(url_for('signup'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/chat_page')
@login_required
def chat_page():
    # The original chat interface will be loaded from index.html
    # We need to make sure the JS in index.html still works.
    # It might need adjustment to handle session-based auth.
    # For now, let's just render it.
    return render_template('index.html')


# The original API endpoint, now connected to OpenAI
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    query = data.get('query')

    try:
        # Note: The OpenAI client will automatically pick up the OPENAI_API_KEY from the environment
        client = openai.OpenAI()

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        )

        ai_response = completion.choices[0].message.content

        response_data = {
            "response": ai_response,
            "sources": [] # No sources for now
        }

    except openai.AuthenticationError as e:
        print(f"OpenAI API authentication error: {e}")
        response_data = {"response": "Sorry, there is an issue with the AI service configuration. The API key may be invalid or missing.", "sources": []}
    except openai.APIError as e:
        # Handle API error here, e.g. retry or log
        print(f"OpenAI API returned an API Error: {e}")
        response_data = {"response": "Sorry, I encountered an error with the AI service. Please check the server logs.", "sources": []}
    except openai.APIConnectionError as e:
        # Handle connection error here
        print(f"Failed to connect to OpenAI API: {e}")
        response_data = {"response": "Sorry, I couldn't connect to the AI service. Please check your network connection.", "sources": []}
    except openai.RateLimitError as e:
        # Handle rate limit error (we recommend using exponential backoff)
        print(f"OpenAI API request exceeded rate limit: {e}")
        response_data = {"response": "Sorry, the request limit has been reached. Please try again later.", "sources": []}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        response_data = {"response": "An unexpected error occurred. Please try again.", "sources": []}

    return jsonify(response_data)

# Function to create the database
def create_db():
    with app.app_context():
        db.create_all()
        print("Database created!")

if __name__ == '__main__':
    # Check if the database file exists, if not, create it
    if not os.path.exists('database.db'):
        create_db()
    app.run(debug=True, port=5000)
