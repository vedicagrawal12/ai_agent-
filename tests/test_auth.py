# pyrefly: ignore [missing-import]
import pytest
from utils.security import login_tracker

def test_signup_success(client):
    """Verify signup with valid details redirects to login."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')

def test_signup_missing_fields(client):
    """Verify missing signup parameters shows warning."""
    resp = client.post('/signup', data={
        'username': '',
        'email': 'newuser@example.com',
        'password': 'password123',
        'phone': '1234567890'
    })
    assert resp.status_code == 200
    assert b"Username, email, password, and contact number are required" in resp.data

    # Test missing phone
    resp2 = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'phone': ''
    })
    assert resp2.status_code == 200
    assert b"Username, email, password, and contact number are required" in resp2.data

def test_signup_invalid_email(client):
    """Verify invalid email string is rejected."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'invalid-email',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    assert resp.status_code == 200
    assert b"Please enter a valid email address" in resp.data

def test_signup_invalid_phone(client):
    """Verify invalid phone formats are rejected."""
    resp = client.post('/signup', data={
        'username': 'phoneuser',
        'email': 'phone@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': 'not-a-phone'
    })
    assert resp.status_code == 200
    assert b"Please enter a valid contact number" in resp.data

def test_signup_weak_password(client):
    """Verify weak passwords under 8 characters are blocked."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'weak',
        'confirm_password': 'weak',
        'phone': '1234567890'
    })
    assert resp.status_code == 200
    assert b"Password must be at least 8 characters long" in resp.data

def test_signup_password_mismatch(client):
    """Verify password mismatches fail registration."""
    resp = client.post('/signup', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password456',
        'phone': '1234567890'
    })
    assert resp.status_code == 200
    assert b"Passwords do not match" in resp.data

def test_signup_duplicate_email(client):
    """Verify duplicate email registrations are blocked."""
    # First signup
    client.post('/signup', data={
        'username': 'user1',
        'email': 'dup@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    # Second signup with same email but different username
    resp = client.post('/signup', data={
        'username': 'user2',
        'email': 'dup@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '0987654321'
    })
    assert resp.status_code == 200
    assert b"Email address is already registered" in resp.data

def test_signup_duplicate_username_allowed(client):
    """Verify duplicate usernames with different emails are allowed."""
    # First signup
    client.post('/signup', data={
        'username': 'sameusername',
        'email': 'user1@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    # Second signup with same username but different email
    resp = client.post('/signup', data={
        'username': 'sameusername',
        'email': 'user2@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '0987654321'
    })
    # Should redirect on success
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')

def test_login_success(client):
    """Verify successful login redirects to dashboard and sets session."""
    # Create user
    client.post('/signup', data={
        'username': 'loginuser',
        'email': 'login@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    # Login
    resp = client.post('/login', data={
        'email': 'login@example.com',
        'password': 'password123'
    })
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')

def test_login_missing_fields(client):
    """Verify login validation works on empty inputs."""
    resp = client.post('/login', data={
        'email': '',
        'password': ''
    })
    assert resp.status_code == 200
    assert b"Email and password are required" in resp.data

def test_login_wrong_password(client):
    """Verify wrong password fails login."""
    client.post('/signup', data={
        'username': 'wrongpass',
        'email': 'wrong@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    resp = client.post('/login', data={
        'email': 'wrong@example.com',
        'password': 'incorrectpassword'
    })
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data

def test_login_lockout(client):
    """Verify failed attempts lock account."""
    email = "lock@example.com"
    client.post('/signup', data={
        'username': 'lockeduser',
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    
    # Fail login 5 times (default threshold is 5 failures)
    for _ in range(5):
        client.post('/login', data={
            'email': email,
            'password': 'incorrect_password'
        })
        
    # The 6th attempt should trigger lockout message
    resp = client.post('/login', data={
        'email': email,
        'password': 'password123'
    })
    assert resp.status_code == 200
    assert b"Account temporarily locked" in resp.data
    
    # Manually clean tracker to avoid pollution
    login_tracker.clear(email)

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

from unittest.mock import patch

@patch("utils.email_sender.is_smtp_configured", return_value=True)
@patch("utils.email_sender._run_in_background", lambda target, *args: target(*args))
@patch("utils.email_sender._send_smtp_email_sync")
def test_signup_triggers_welcome_email(mock_send, mock_config, client):
    """Verify that a successful signup triggers a welcome email."""
    mock_send.return_value = True
    resp = client.post('/signup', data={
        'username': 'welcomeuser',
        'email': 'welcome@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    assert resp.status_code == 302
    assert mock_send.called
    assert mock_send.call_args[0][0] == "welcome@example.com"
    assert "Welcome" in mock_send.call_args[0][1]

@patch("utils.email_sender.is_smtp_configured", return_value=True)
@patch("utils.email_sender._run_in_background", lambda target, *args: target(*args))
@patch("utils.email_sender._send_smtp_email_sync")
def test_forgot_password_and_otp_reset_flow(mock_send, mock_config, client, db):
    """Verify forgot password OTP creation, verification, and reset flow."""
    mock_send.return_value = True
    
    # 1. Register user
    client.post('/signup', data={
        'username': 'resetuser',
        'email': 'reset@example.com',
        'password': 'old_password_123',
        'confirm_password': 'old_password_123',
        'phone': '1234567890'
    })
    
    mock_send.reset_mock()
    
    # 2. Trigger forgot password
    resp = client.post('/forgot-password', data={
        'email': 'reset@example.com'
    })
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/verify-otp')
    assert mock_send.called
    assert mock_send.call_args[0][0] == "reset@example.com"
    assert "Reset" in mock_send.call_args[0][1]
    
    # Retrieve OTP directly from DB
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT otp FROM password_resets WHERE email = 'reset@example.com';")
    otp_row = cursor.fetchone()
    db._release_connection(conn)
    
    assert otp_row is not None
    otp = otp_row[0]
    
    # 3. Verify OTP with invalid code
    resp_invalid = client.post('/verify-otp', data={
        'otp': '000000'
    })
    assert resp_invalid.status_code == 200
    assert b"Invalid or expired OTP" in resp_invalid.data
    
    # 4. Verify OTP with valid code
    resp_valid = client.post('/verify-otp', data={
        'otp': otp
    })
    assert resp_valid.status_code == 302
    assert resp_valid.headers['Location'].endswith('/reset-password')
    
    # 5. Reset password
    resp_reset = client.post('/reset-password', data={
        'password': 'new_secure_password_123',
        'confirm_password': 'new_secure_password_123'
    })
    assert resp_reset.status_code == 302
    assert resp_reset.headers['Location'].endswith('/login')
    
    # 6. Try to log in with new password
    resp_login = client.post('/login', data={
        'email': 'reset@example.com',
        'password': 'new_secure_password_123'
    })
    assert resp_login.status_code == 302
    assert resp_login.headers['Location'].endswith('/')
