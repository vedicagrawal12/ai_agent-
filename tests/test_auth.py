# pyrefly: ignore [missing-import]
import pytest
from utils.security import login_tracker

def test_signup_success(client):
    """Verify signup with valid details redirects to login."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')

def test_signup_missing_fields(client):
    """Verify missing signup parameters shows warning."""
    resp = client.post('/signup', data={
        'username': '',
        'email': 'newuser@example.com',
        'password': 'password123'
    })
    assert resp.status_code == 200
    assert b"Username, email, and password are required" in resp.data

def test_signup_invalid_email(client):
    """Verify invalid email string is rejected."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'invalid-email',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert resp.status_code == 200
    assert b"Please enter a valid email address" in resp.data

def test_signup_weak_password(client):
    """Verify weak passwords under 8 characters are blocked."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'weak',
        'confirm_password': 'weak'
    })
    assert resp.status_code == 200
    assert b"Password must be at least 8 characters long" in resp.data

def test_signup_password_mismatch(client):
    """Verify password mismatches fail registration."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password456'
    })
    assert resp.status_code == 200
    assert b"Passwords do not match" in resp.data

def test_signup_duplicate_username(client):
    """Verify duplicate registrations are blocked."""
    # First signup
    client.post('/signup', data={
        'username': 'duplicateuser',
        'email': 'dup@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    # Second signup with same username
    resp = client.post('/signup', data={
        'username': 'duplicateuser',
        'email': 'dup2@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert resp.status_code == 200
    assert b"Username already exists" in resp.data

def test_login_success(client):
    """Verify successful login redirects to dashboard and sets session."""
    # Create user
    client.post('/signup', data={
        'username': 'loginuser',
        'email': 'login@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    # Login
    resp = client.post('/login', data={
        'username': 'loginuser',
        'password': 'password123'
    })
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')

def test_login_missing_fields(client):
    """Verify login validation works on empty inputs."""
    resp = client.post('/login', data={
        'username': '',
        'password': ''
    })
    assert resp.status_code == 200
    assert b"Username and password are required" in resp.data

def test_login_wrong_password(client):
    """Verify wrong password fails login."""
    client.post('/signup', data={
        'username': 'wrongpass',
        'email': 'wrong@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    resp = client.post('/login', data={
        'username': 'wrongpass',
        'password': 'incorrectpassword'
    })
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data

def test_login_lockout(client):
    """Verify failed attempts lock account."""
    username = "lockeduser"
    client.post('/signup', data={
        'username': username,
        'email': 'lock@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    
    # Fail login 5 times (default threshold is 5 failures)
    for _ in range(5):
        client.post('/login', data={
            'username': username,
            'password': 'incorrect_password'
        })
        
    # The 6th attempt should trigger lockout message
    resp = client.post('/login', data={
        'username': username,
        'password': 'password123'
    })
    assert resp.status_code == 200
    assert b"Account temporarily locked" in resp.data
    
    # Manually clean tracker to avoid pollution
    login_tracker.clear(username)

def test_logout(auth_client):
    """Verify logout clears session and redirects to login."""
    resp = auth_client.get('/logout')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')

def test_auth_middleware_redirects_unauthenticated(client):
    """Verify unauthenticated access to dashboard/api is blocked."""
    # Web page gets redirected
    resp = client.get('/verify-db')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')
    
    # API endpoints get 401 Unauthorized
    resp = client.get('/api/leads')
    assert resp.status_code == 401
    assert resp.json == {"error": "Unauthorized. Please login."}
