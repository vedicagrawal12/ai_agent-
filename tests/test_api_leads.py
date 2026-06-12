# pyrefly: ignore [missing-import]
import pytest
from collectors.base_collector import Lead
from datetime import date, timedelta

def test_get_leads_empty(auth_client):
    """Verify empty leads list on initialization."""
    resp = auth_client.get('/api/leads')
    assert resp.status_code == 200
    assert resp.json["success"] is True
    assert resp.json["leads"] == []

def test_search_missing_query(auth_client):
    """Verify search payload validation checks query."""
    resp = auth_client.post('/api/search', json={"city": "Bhopal"})
    assert resp.status_code == 400
    assert "Please enter a business type/keyword" in resp.json["error"]

def test_search_missing_city(auth_client):
    """Verify search payload validation checks city."""
    resp = auth_client.post('/api/search', json={"query": "gyms"})
    assert resp.status_code == 400
    assert "Please enter a city name" in resp.json["error"]

def test_delete_lead(auth_client, db):
    """Verify lead deletion removes the record."""
    # Register/fetch testuser ID
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Save a lead
    lead = Lead(name="Delete Gym", place_id="place_del", city="Bhopal")
    db.save_leads([lead], user_id)
    
    # Fetch lead to get DB auto-increment ID
    saved_leads = db.get_all_leads(user_id=user_id)
    assert len(saved_leads) == 1
    db_id = saved_leads[0]["id"]
    
    # Delete lead via API
    resp = auth_client.delete(f'/api/leads/{db_id}')
    assert resp.status_code == 200
    assert resp.json["success"] is True
    
    # Verify it is deleted
    assert len(db.get_all_leads(user_id=user_id)) == 0

def test_delete_lead_cross_user(client, db):
    """Verify that User A cannot delete User B's lead."""
    # Create User A
    client.post('/signup', data={'username': 'usera', 'email': 'usera@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_a = db.get_user_by_username("usera")
    
    # Create User B
    client.post('/signup', data={'username': 'userb', 'email': 'userb@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_b = db.get_user_by_username("userb")
    
    # Save a lead for User A
    lead_a = Lead(name="User A Gym", place_id="place_a", city="Bhopal")
    db.save_leads([lead_a], user_a["id"])
    saved_lead = db.get_all_leads(user_id=user_a["id"])[0]
    
    # Log in as User B
    client.post('/login', data={'email': 'userb@example.com', 'password': 'password123'})
    
    # Try to delete User A's lead using User B's credentials
    resp = client.delete(f'/api/leads/{saved_lead["id"]}')
    assert resp.status_code == 200  # API returns success but filters by user_id inside delete_lead
    
    # Verify User A's lead was NOT deleted
    assert len(db.get_all_leads(user_id=user_a["id"])) == 1

def test_pipeline_update(auth_client, db):
    """Verify updating stage to PITCHED sets contacted to True."""
    user = db.get_user_by_username("testuser")
    
    lead = Lead(name="Pipeline Gym", place_id="place_pipe", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    # Update pipeline to PITCHED
    resp = auth_client.post(f'/api/leads/{saved_lead["id"]}/pipeline', json={"stage": "PITCHED"})
    assert resp.status_code == 200
    assert resp.json["stage"] == "PITCHED"
    
    # Check updated lead in DB
    updated = db.get_lead_by_id(saved_lead["id"], user_id=user["id"])
    assert updated["pipeline_stage"] == "PITCHED"
    assert updated["contacted"] is True

def test_pipeline_invalid_stage(auth_client, db):
    """Verify invalid pipeline stage payload is blocked."""
    user = db.get_user_by_username("testuser")
    lead = Lead(name="Pipeline Gym", place_id="place_pipe", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    resp = auth_client.post(f'/api/leads/{saved_lead["id"]}/pipeline', json={"stage": "INVALID_STAGE"})
    assert resp.status_code == 400
    assert "Invalid pipeline stage" in resp.json["error"]

def test_schedule_reminder_days(auth_client, db):
    """Verify reminder scheduling via relative days."""
    user = db.get_user_by_username("testuser")
    lead = Lead(name="Reminder Gym", place_id="place_rem", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    resp = auth_client.post(f'/api/leads/{saved_lead["id"]}/schedule-reminder', json={"days": 3})
    assert resp.status_code == 200
    assert resp.json["success"] is True
    
    expected_date = (date.today() + timedelta(days=3)).isoformat()
    assert resp.json["remind_date"] == expected_date
    
    # Verify database update
    updated = db.get_lead_by_id(saved_lead["id"], user_id=user["id"])
    assert str(updated["remind_date"]) == expected_date
    assert updated["remind_status"] == "PENDING"

def test_schedule_reminder_custom_date(auth_client, db):
    """Verify reminder scheduling via specific date."""
    user = db.get_user_by_username("testuser")
    lead = Lead(name="Reminder Gym", place_id="place_rem", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    custom_target = "2026-12-25"
    resp = auth_client.post(f'/api/leads/{saved_lead["id"]}/schedule-reminder', json={"custom_date": custom_target})
    assert resp.status_code == 200
    
    updated = db.get_lead_by_id(saved_lead["id"], user_id=user["id"])
    assert str(updated["remind_date"]) == custom_target

def test_schedule_reminder_invalid_date(auth_client, db):
    """Verify invalid custom date format fails validation."""
    user = db.get_user_by_username("testuser")
    lead = Lead(name="Reminder Gym", place_id="place_rem", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    resp = auth_client.post(f'/api/leads/{saved_lead["id"]}/schedule-reminder', json={"custom_date": "invalid-format"})
    assert resp.status_code == 400
    assert "Expected YYYY-MM-DD" in resp.json["error"]

def test_dismiss_reminder(auth_client, db):
    """Verify reminder status transitions to DISMISSED."""
    user = db.get_user_by_username("testuser")
    lead = Lead(name="Reminder Gym", place_id="place_rem", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    # Schedule reminder first
    db.schedule_reminder(saved_lead["id"], "2026-06-30", user["id"])
    
    # Dismiss it
    resp = auth_client.post(f'/api/leads/{saved_lead["id"]}/dismiss-reminder')
    assert resp.status_code == 200
    
    updated = db.get_lead_by_id(saved_lead["id"], user_id=user["id"])
    assert updated["remind_status"] == "DISMISSED"
