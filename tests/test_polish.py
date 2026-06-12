# pyrefly: ignore [missing-import]
import pytest
import io
import json
from unittest.mock import patch
from collectors.base_collector import Lead

def test_deactivated_user_login(client, db):
    """Verify that deactivated user login attempts fail and show error."""
    # Create user via signup
    client.post('/signup', data={
        'username': 'deactuser',
        'email': 'deact@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    user = db.get_user_by_username("deactuser")
    
    # Deactivate user
    db.toggle_user_active(user["id"], False)
    
    # Try to login
    resp = client.post('/login', data={
        'email': 'deact@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert resp.status_code == 200
    assert b"deactivated" in resp.data or b"Please contact an admin" in resp.data
 
def test_delete_user_account(client, db):
    """Verify delete account endpoint deletes the user and cascades related records."""
    # Sign up and login
    client.post('/signup', data={
        'username': 'deluser',
        'email': 'del@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    client.post('/login', data={
        'email': 'del@example.com',
        'password': 'password123'
    })
    
    user = db.get_user_by_username("deluser")
    user_id = user["id"]
    
    # Save a lead, search, and message log for this user
    lead = Lead(name="Test Gym", place_id="test_place_id", city="Bhopal")
    db.save_leads([lead], user_id)
    saved_lead = db.get_all_leads(user_id=user_id)[0]
    
    db.save_search("gyms", "Bhopal", 1, 1, user_id)
    db.log_message(saved_lead["id"], "whatsapp_intro", "Hello!", user_id)
    
    # Confirm records exist
    assert len(db.get_all_leads(user_id=user_id)) == 1
    assert len(db.get_search_history(user_id=user_id)) == 1
    
    # Send delete request
    resp = client.delete('/api/config/delete-account')
    assert resp.status_code == 200
    assert resp.json["success"] is True
    
    # Verify records deleted (cascade delete checks)
    assert db.get_user_by_username("deluser") is None
    
    # Query database to confirm leads, searches, logs are cleaned up
    conn = db._get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM leads WHERE user_id = %s", (user_id,))
        assert cursor.fetchone()[0] == 0
        
        cursor.execute("SELECT COUNT(*) FROM search_history WHERE user_id = %s", (user_id,))
        assert cursor.fetchone()[0] == 0
        
        cursor.execute("SELECT COUNT(*) FROM message_log WHERE user_id = %s", (user_id,))
        assert cursor.fetchone()[0] == 0
    finally:
        db._release_connection(conn)


def test_export_user_data(client, db):
    """Verify data portability export endpoint yields correct user history structure."""
    # Sign up and login
    client.post('/signup', data={
        'username': 'exportuser',
        'email': 'export@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    client.post('/login', data={
        'email': 'export@example.com',
        'password': 'password123'
    })
    
    user = db.get_user_by_username("exportuser")
    user_id = user["id"]
    
    lead = Lead(name="Export Gym", place_id="export_place", city="Bhopal")
    db.save_leads([lead], user_id)
    saved_lead = db.get_all_leads(user_id=user_id)[0]
    
    db.save_search("gyms", "Bhopal", 1, 1, user_id)
    db.log_message(saved_lead["id"], "whatsapp_intro", "Export hello!", user_id)
    
    # Request export
    resp = client.get('/api/config/export-data')
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("Content-Disposition", "")
    
    payload = json.loads(resp.data.decode("utf-8"))
    assert "user" in payload
    assert payload["user"]["username"] == "exportuser"
    assert len(payload["leads"]) == 1
    assert payload["leads"][0]["name"] == "Export Gym"
    assert len(payload["search_history"]) == 1
    assert len(payload["message_log"]) == 1

def test_csv_lead_importer(client, db):
    """Verify CSV parser standardizes headers, phone digits, priority, and performs bulk insertion."""
    # Sign up and login
    client.post('/signup', data={
        'username': 'csvuser',
        'email': 'csv@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    client.post('/login', data={
        'email': 'csv@example.com',
        'password': 'password123'
    })
    
    csv_data = (
        "Name,Phone,Email,Website,Address,City,Priority,Place_ID\n"
        "Raw Gym,09876543210,invalid_email,http://raw.com,123 Street,Bhopal,high,raw_place_1\n"
        "Second Gym,+91 99999 88888,valid@email.com,,456 Road,,invalid_priority,\n"
    )
    
    # Upload CSV file
    resp = client.post('/api/leads/import', data={
        'file': (io.BytesIO(csv_data.encode('utf-8')), 'test_leads.csv')
    }, content_type='multipart/form-data')
    
    assert resp.status_code == 200
    assert resp.json["success"] is True
    assert resp.json["imported_count"] == 2
    
    user = db.get_user_by_username("csvuser")
    leads = db.get_all_leads(user_id=user["id"])
    assert len(leads) == 2
    
    # Check phone number standardization and data cleanliness
    lead1 = next(l for l in leads if l["place_id"] == "raw_place_1")
    assert lead1["name"] == "Raw Gym"
    assert lead1["phone"] == "+91 98765 43210"  # Standardized from 09876543210
    assert lead1["email"] == ""  # Invalid email cleaned
    assert lead1["priority"] == "HIGH"
    
    lead2 = next(l for l in leads if l["place_id"] != "raw_place_1")
    assert lead2["name"] == "Second Gym"
    assert lead2["phone"] == "+91 99999 88888"
    assert lead2["email"] == "valid@email.com"
    assert lead2["priority"] == "LOW"  # Invalid priority fell back to LOW
    assert lead2["city"] == "Unknown"  # Empty city fell back to Unknown
    assert lead2["place_id"].startswith("imported_")  # Auto-generated Place ID

def test_admin_dashboard_operations(client, db):
    """Verify admin routes access control, toggling is_active/is_admin, and safety guards."""
    # 1. Non-admin client access control checks
    # Sign up both users while unauthenticated to avoid login redirects
    client.post('/signup', data={'username': 'regular', 'email': 'reg@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    client.post('/signup', data={'username': 'regular2', 'email': 'reg2@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    
    client.post('/login', data={'email': 'reg@example.com', 'password': 'password123'})
    
    # Try to access admin dashboard as regular user
    resp = client.get('/admin')
    assert resp.status_code == 302  # redirects or blocks
    
    # Try to toggle admin status as regular user
    resp = client.post('/api/admin/users/1/toggle-active', json={"active": False})
    assert resp.status_code == 403
    
    # 2. Admin operations
    # Log out regular, promote regular to admin, and log back in
    client.get('/logout')
    
    admin_user = db.get_user_by_username("regular")
    target_user = db.get_user_by_username("regular2")
    
    # Promote admin_user to admin in DB
    db.toggle_user_admin(admin_user["id"], True)
    admin_user = db.get_user_by_username("regular")
    
    # Assert regular is now admin and regular2 is not
    assert admin_user["is_admin"] is True
    assert target_user["is_admin"] is False
    
    # Log in as admin_user
    client.post('/login', data={'email': 'reg@example.com', 'password': 'password123'})
    
    # Access dashboard
    resp = client.get('/admin')
    assert resp.status_code == 200
    assert b"Admin Control Console" in resp.data or b"Operator Accounts" in resp.data
    
    # Toggle target_user inactive
    resp = client.post(f'/api/admin/users/{target_user["id"]}/toggle-active', json={"active": False})
    assert resp.status_code == 200
    assert db.get_user_by_username("regular2")["is_active"] is False
    
    # Toggle target_user active again
    resp = client.post(f'/api/admin/users/{target_user["id"]}/toggle-active', json={"active": True})
    assert resp.status_code == 200
    assert db.get_user_by_username("regular2")["is_active"] is True
    
    # Toggle target_user admin privilege to True
    resp = client.post(f'/api/admin/users/{target_user["id"]}/toggle-admin', json={"admin": True})
    assert resp.status_code == 200
    assert db.get_user_by_username("regular2")["is_admin"] is True
    
    # 3. Test safety guards (cannot toggle self)
    # Try to deactivate self
    resp = client.post(f'/api/admin/users/{admin_user["id"]}/toggle-active', json={"active": False})
    assert resp.status_code == 400
    assert "deactivate your own account" in resp.json["error"]
    
    # Try to modify own admin status
    resp = client.post(f'/api/admin/users/{admin_user["id"]}/toggle-admin', json={"admin": False})
    assert resp.status_code == 400
    assert "modify your own admin privileges" in resp.json["error"]

@patch("utils.ai_writer.AIOutreachWriter._call_gemini_api")
def test_multilanguage_pitch_generation(mock_call_api, client, db):
    """Verify that multi-language settings (Hinglish, English, Hindi) generate pitches with correct prompt guidelines."""
    # Set mock response
    mock_call_api.return_value = "Mock Generated Pitch Content"
    
    # Sign up and login
    client.post('/signup', data={'username': 'pitchuser', 'email': 'pitch@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    client.post('/login', data={'email': 'pitch@example.com', 'password': 'password123'})
    
    lead_data = {
        "id": 1,
        "name": "Pitch Gym",
        "city": "Bhopal",
        "category": "Gym",
        "rating": "4.5",
        "reviews": "120"
    }
    
    # Test Hinglish pitch generation
    resp = client.post('/api/outreach/generate-ai', json={
        "lead": lead_data,
        "tone": "elite",
        "service": "web_design",
        "language": "hinglish"
    }, headers={"X-Gemini-API-Key": "AIzaDummyKey123"})
    assert resp.status_code == 200
    assert resp.json["pitch"] == "Mock Generated Pitch Content"
    # Verify the prompt contained Hinglish language instructions
    called_prompt = mock_call_api.call_args_list[-1][0][0]
    assert "Hinglish" in called_prompt
    
    # Test English pitch generation
    resp = client.post('/api/outreach/generate-ai', json={
        "lead": lead_data,
        "tone": "friendly",
        "service": "seo",
        "language": "english"
    }, headers={"X-Gemini-API-Key": "AIzaDummyKey123"})
    assert resp.status_code == 200
    called_prompt = mock_call_api.call_args_list[-1][0][0]
    assert "English" in called_prompt
    assert "SEO" in called_prompt
    
    # Test Hindi pitch generation
    resp = client.post('/api/outreach/generate-ai', json={
        "lead": lead_data,
        "tone": "direct",
        "service": "gmb",
        "language": "hindi"
    }, headers={"X-Gemini-API-Key": "AIzaDummyKey123"})
    assert resp.status_code == 200
    called_prompt = mock_call_api.call_args_list[-1][0][0]
    assert "Hindi" in called_prompt
    assert "Devanagari" in called_prompt

def test_errors_404_handler(client):
    """Verify that a request to an invalid URL renders 404.html with status 404 (BUG-H6)."""
    resp = client.get('/some-nonexistent-page-url')
    assert resp.status_code == 404
    assert b"Lost in Space" in resp.data
    assert b"404" in resp.data
    assert b"Dashboard" in resp.data

    # For API 404s, it should return JSON (as defined in errors.py)
    api_resp = client.get('/api/some-nonexistent-api-url')
    assert api_resp.status_code == 404
    assert api_resp.json == {"error": "Resource not found"}

@patch("utils.task_runner.TaskRunner.submit")
def test_zones_input_sanitization(mock_submit, client, db):
    """Verify that zones are sanitized before background task submission (BUG-L9)."""
    # Sign up and login
    client.post('/signup', data={'username': 'zoneuser', 'email': 'zone@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    client.post('/login', data={'email': 'zone@example.com', 'password': 'password123'})

    mock_submit.return_value = "dummy-task-id"

    # 15 zones, some with special characters, some too long
    dirty_zones = [
        "A" * 100,  # too long (should slice to 50)
        "MP Nagar; DROP TABLE users;",  # special chars (should keep only alphanumeric, spaces, hyphens, dots)
        "Kolar-Road 123",  # valid
        "Valid.Zone",  # valid
    ] + [f"Zone {i}" for i in range(15)]  # total > 10 zones (should slice to 10)

    client.post('/api/search', json={
        "query": "gym",
        "city": "Bhopal",
        "zones": dirty_zones,
        "deep_scan": True
    }, headers={"X-SerpApi-Key": "DummySerpKey"})

    assert mock_submit.called
    called_kwargs = mock_submit.call_args[1]
    sanitized_zones = called_kwargs["zones"]

    # Verify limit of 10
    assert len(sanitized_zones) == 10
    
    # Verify first zone was sliced to 50 chars
    assert sanitized_zones[0] == "A" * 50
    
    # Verify special chars removed (only keeps alphanumeric, space, hyphens, dots)
    assert sanitized_zones[1] == "MP Nagar DROP TABLE users"
    
    # Verify valid zones kept
    assert sanitized_zones[2] == "Kolar-Road 123"
    assert sanitized_zones[3] == "Valid.Zone"

def test_csv_lead_deterministic_place_id(client, db):
    """Verify that CSV imports without place_id generate deterministic place_ids (BUG-L10)."""
    # Sign up and login
    client.post('/signup', data={'username': 'detuser', 'email': 'det@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    client.post('/login', data={'email': 'det@example.com', 'password': 'password123'})

    csv_data = (
        "Name,Phone,Email,Website,Address,City,Priority,Place_ID\n"
        "Duplicate Gym,1234567890,dup@example.com,http://dup.com,Street 1,Delhi,low,\n"
    )

    resp1 = client.post('/api/leads/import', data={
        'file': (io.BytesIO(csv_data.encode('utf-8')), 'leads1.csv')
    }, content_type='multipart/form-data')
    assert resp1.status_code == 200
    assert resp1.json["imported_count"] == 1

    user = db.get_user_by_username("detuser")
    leads1 = db.get_all_leads(user_id=user["id"])
    assert len(leads1) == 1
    place_id_1 = leads1[0]["place_id"]

    import hashlib
    # expected input combines: lower name, lower city, standardized phone (+91 12345 67890)
    expected_input = "duplicate gym_delhi_+91 12345 67890"
    expected_hash = hashlib.md5(expected_input.encode('utf-8')).hexdigest()[:16]
    expected_place_id = f"imported_{expected_hash}"

    assert place_id_1 == expected_place_id

def test_admin_user_pagination(client, db):
    """Verify that the admin route pagination limits user query results (BUG-L12)."""
    # Create admin
    client.post('/signup', data={'username': 'adminop', 'email': 'adminop@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    admin = db.get_user_by_username("adminop")
    db.toggle_user_admin(admin["id"], True)

    client.post('/login', data={'email': 'adminop@example.com', 'password': 'password123'})

    # Create 15 regular users (total 16 users)
    for i in range(15):
        db.create_user(f"user_{i}", f"user_{i}@example.com", "hash123")

    resp1 = client.get('/admin?page=1')
    assert resp1.status_code == 200
    assert b"Page 1 of 2" in resp1.data

    resp2 = client.get('/admin?page=2')
    assert resp2.status_code == 200
    assert b"Page 2 of 2" in resp2.data
