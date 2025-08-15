import os
import pytest
from app import app, db, User
import openai

@pytest.fixture(scope='function')
def test_client():
    # Configure the app for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_database.db'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing forms

    with app.test_client() as testing_client:
        with app.app_context():
            db.create_all()
        yield testing_client  # this is where the testing happens!
        with app.app_context():
            db.drop_all()

    # Cleanup the test database file
    if os.path.exists('test_database.db'):
        os.remove('test_database.db')


def test_signup_page(test_client):
    """Test that the signup page loads."""
    response = test_client.get('/signup')
    assert response.status_code == 200
    assert b"Sign Up" in response.data

def test_login_page(test_client):
    """Test that the login page loads."""
    response = test_client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data

def test_user_signup(test_client):
    """Test user registration."""
    response = test_client.post('/signup', data=dict(
        username='testuser',
        password='password'
    ), follow_redirects=True)
    assert response.status_code == 200
    assert b"Your account has been created!" in response.data
    # Check that the user is now in the database
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None

def test_user_login_logout(test_client):
    """Test user login and logout functionality."""
    # First, sign up a user to log in with
    test_client.post('/signup', data=dict(
        username='loginuser',
        password='password'
    ), follow_redirects=True)

    # Test login
    response = test_client.post('/login', data=dict(
        username='loginuser',
        password='password'
    ), follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome to your Dashboard, loginuser!' in response.data # Should be on the dashboard page
    assert b'Logout' in response.data # The logout link is on the dashboard

    # Test logout
    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data # Should be redirected to login page

def test_protected_routes(test_client):
    """Test that chat page and API are protected."""
    # Test /chat_page
    response = test_client.get('/chat_page', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data # Should be redirected to login

    # Test /chat API is protected
    response = test_client.post('/chat', json={'query': 'hello'})
    assert response.status_code == 302 # Should redirect to login


def test_dashboard_page(test_client):
    """Test that the dashboard is protected and works after login."""
    # Test unauthenticated access
    response = test_client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data

    # Sign up and log in a user
    test_client.post('/signup', data=dict(username='dashuser', password='password'), follow_redirects=True)
    response = test_client.post('/login', data=dict(username='dashuser', password='password'), follow_redirects=True)

    # Check if we landed on the dashboard
    assert response.status_code == 200
    assert b"Welcome to your Dashboard, dashuser!" in response.data
    assert b"Go to AI Chat" in response.data


def test_settings_page(test_client):
    """Test that the settings page is protected and works after login."""
    # Test unauthenticated access
    response = test_client.get('/settings', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data

    # Sign up and log in a user
    test_client.post('/signup', data=dict(username='settingsuser', password='password'), follow_redirects=True)
    response = test_client.post('/login', data=dict(username='settingsuser', password='password'), follow_redirects=True)

    # Now that we are logged in, navigate to the settings page
    response = test_client.get('/settings')
    assert response.status_code == 200
    assert b"User Settings for settingsuser" in response.data
    assert b"Change Password" in response.data


def test_chat_api_success(test_client, mocker):
    """Test the /chat endpoint with a mocked successful API call."""
    # Mock the OpenAI client and its response
    mock_openai_client = mocker.patch('openai.OpenAI')

    # Create a mock object that mimics the structure of the OpenAI response
    mock_choice = mocker.Mock()
    mock_choice.message.content = "This is a mocked AI response."
    mock_completion = mocker.Mock()
    mock_completion.choices = [mock_choice]

    mock_openai_client.return_value.chat.completions.create.return_value = mock_completion

    # Sign up and log in a user
    test_client.post('/signup', data=dict(username='chattester', password='password'))
    test_client.post('/login', data=dict(username='chattester', password='password'))

    # Call the chat endpoint
    response = test_client.post('/chat', json={'query': 'hello from test'})

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['response'] == "This is a mocked AI response."
    assert mock_openai_client.return_value.chat.completions.create.called


def test_chat_api_auth_error(test_client, mocker):
    """Test the /chat endpoint with a mocked AuthenticationError."""
    # Mock the OpenAI client's create method to raise an AuthenticationError
    mock_openai_client = mocker.patch('openai.OpenAI')
    mock_openai_client.return_value.chat.completions.create.side_effect = openai.AuthenticationError(message="Invalid API key.", response=mocker.Mock(), body=None)

    # Sign up and log in a user
    test_client.post('/signup', data=dict(username='erroruser', password='password'))
    test_client.post('/login', data=dict(username='erroruser', password='password'))

    # Call the chat endpoint
    response = test_client.post('/chat', json={'query': 'another test'})

    assert response.status_code == 200
    json_data = response.get_json()
    assert "The API key may be invalid or missing" in json_data['response']
