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
