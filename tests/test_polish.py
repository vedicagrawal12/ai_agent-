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
        'confirm_password': 'password123'
    })
    user = db.get_user_by_username("deactuser")
    
    # Deactivate user
    db.toggle_user_active(user["id"], False)
    
    # Try to login
    resp = client.post('/login', data={
        'username': 'deactuser',
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
        'confirm_password': 'password123'
    })
    client.post('/login', data={
        'username': 'deluser',
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
        'confirm_password': 'password123'
    })
    client.post('/login', data={
        'username': 'exportuser',
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
        'confirm_password': 'password123'
    })
    client.post('/login', data={
        'username': 'csvuser',
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
    client.post('/signup', data={'username': 'regular', 'email': 'reg@example.com', 'password': 'password123', 'confirm_password': 'password123'})
    client.post('/signup', data={'username': 'regular2', 'email': 'reg2@example.com', 'password': 'password123', 'confirm_password': 'password123'})
    
    client.post('/login', data={'username': 'regular', 'password': 'password123'})
    
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
    client.post('/login', data={'username': 'regular', 'password': 'password123'})
    
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
    client.post('/signup', data={'username': 'pitchuser', 'email': 'pitch@example.com', 'password': 'password123', 'confirm_password': 'password123'})
    client.post('/login', data={'username': 'pitchuser', 'password': 'password123'})
    
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
