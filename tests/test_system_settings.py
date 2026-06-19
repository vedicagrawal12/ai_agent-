import pytest
from unittest.mock import patch

def test_db_settings_helpers(db):
    """Verify get/save system settings helpers on Database instance."""
    assert db.get_system_setting("non_existent_key", "default_val") == "default_val"
    
    # Save a setting
    assert db.save_system_setting("test_key", "val123") is True
    assert db.get_system_setting("test_key") == "val123"
    
    # Overwrite the setting
    assert db.save_system_setting("test_key", "val456") is True
    assert db.get_system_setting("test_key") == "val456"

def test_api_config_non_admin(auth_client, db):
    """Verify /api/config masks key and hides details for non-admin operators."""
    # Setup key in DB
    db.save_system_setting("serpapi_key", "real-serpapi-key-from-db-12345")
    
    resp = auth_client.get('/api/config')
    assert resp.status_code == 200
    assert resp.json["has_api_key"] is True
    assert resp.json["masked_key"] == "" # Masked key must be empty for normal users

def test_api_config_admin(client, db):
    """Verify /api/config exposes masked key to admin operators."""
    # Register and log in as admin user
    client.post('/signup', data={
        'username': 'adminuser',
        'email': 'admin@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    # Set admin status to True directly in DB
    admin = db.get_user_by_username("adminuser")
    db.toggle_user_admin(admin["id"], True)
    
    # Login
    client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'password123'
    })
    
    # Set key in DB
    db.save_system_setting("serpapi_key", "super-secret-admin-key-99999")
    
    resp = client.get('/api/config')
    assert resp.status_code == 200
    assert resp.json["has_api_key"] is True
    # Key length > 12: should mask first 8 and last 4
    assert resp.json["masked_key"] == "super-se...9999"

def test_update_admin_serpapi_key_unauthorized(auth_client):
    """Verify non-admin users cannot call the admin config API."""
    resp = auth_client.post('/api/admin/config/serpapi', json={"api_key": "some-key"})
    assert resp.status_code == 403 # Forbidden (Admin required)

def test_update_admin_serpapi_key_validation_failure(client, db):
    """Verify admin config API rejects invalid keys with status 400."""
    # Register and login admin
    client.post('/signup', data={
        'username': 'adminuser',
        'email': 'admin@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    admin = db.get_user_by_username("adminuser")
    db.toggle_user_admin(admin["id"], True)
    client.post('/login', data={'email': 'admin@example.com', 'password': 'password123'})
    
    # Mock requests.get to return a mock response with status 401 (invalid key)
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 401
        
        resp = client.post('/api/admin/config/serpapi', json={"api_key": "invalid-key"})
        assert resp.status_code == 400
        assert "Invalid SerpApi key" in resp.json["error"]
        
        # Verify db key was not updated/saved
        assert db.get_system_setting("serpapi_key") == ""

def test_update_admin_serpapi_key_success(client, db):
    """Verify admin config API validates and saves valid keys."""
    client.post('/signup', data={
        'username': 'adminuser',
        'email': 'admin@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    admin = db.get_user_by_username("adminuser")
    db.toggle_user_admin(admin["id"], True)
    client.post('/login', data={'email': 'admin@example.com', 'password': 'password123'})
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        
        resp = client.post('/api/admin/config/serpapi', json={"api_key": "valid-serpapi-key-123456"})
        assert resp.status_code == 200
        assert resp.json["success"] is True
        
        # Verify db key was updated
        assert db.get_system_setting("serpapi_key") == "valid-serpapi-key-123456"

def test_masked_password_preservation(client, db):
    """Verify SMTP and IMAP config updates do not overwrite correct passwords with masked values."""
    # Register and login a test user
    client.post('/signup', data={
        'username': 'testconfiguser',
        'email': 'config@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    client.post('/login', data={'email': 'config@example.com', 'password': 'password123'})
    
    # 1. Save original SMTP and IMAP settings
    resp = client.post('/api/config/smtp', json={
        "host": "smtp.example.com",
        "port": 465,
        "email": "config@example.com",
        "password": "original_smtp_pass_123",
        "use_ssl": True
    })
    assert resp.status_code == 200
    
    resp = client.post('/api/config/imap', json={
        "host": "imap.example.com",
        "port": 993,
        "email": "config@example.com",
        "password": "original_imap_pass_456",
        "use_ssl": True
    })
    assert resp.status_code == 200

    # 2. Verify GET returns masked passwords
    resp = client.get('/api/config/smtp')
    assert resp.status_code == 200
    masked_smtp = resp.json["password"]
    assert masked_smtp != "original_smtp_pass_123"
    assert "*" in masked_smtp

    resp = client.get('/api/config/imap')
    assert resp.status_code == 200
    masked_imap = resp.json["password"]
    assert masked_imap != "original_imap_pass_456"
    assert "*" in masked_imap

    # 3. Save again using the masked passwords (simulating clicking "Save" without changing the password)
    resp = client.post('/api/config/smtp', json={
        "host": "smtp.newhost.com",
        "port": 587,
        "email": "config@example.com",
        "password": masked_smtp,
        "use_ssl": False
    })
    assert resp.status_code == 200

    resp = client.post('/api/config/imap', json={
        "host": "imap.newhost.com",
        "port": 143,
        "email": "config@example.com",
        "password": masked_imap,
        "use_ssl": False
    })
    assert resp.status_code == 200

    # 4. Fetch settings directly from the DB helper to confirm the original unmasked passwords were preserved
    user = db.get_user_by_email("config@example.com")
    assert user is not None
    
    smtp_db = db.get_smtp_settings(user["id"])
    assert smtp_db["password"] == "original_smtp_pass_123" # Preserved!
    assert smtp_db["host"] == "smtp.newhost.com" # Updated!
    assert smtp_db["port"] == 587 # Updated!

    imap_db = db.get_imap_settings(user["id"])
    assert imap_db["password"] == "original_imap_pass_456" # Preserved!
    assert imap_db["host"] == "imap.newhost.com" # Updated!
    assert imap_db["port"] == 143 # Updated!
