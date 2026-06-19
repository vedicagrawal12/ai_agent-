# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from collectors.base_collector import Lead

def test_search_history_isolation(client, db):
    """Verify that User A's search history is completely invisible to User B."""
    # 1. Create User A and add search history
    client.post('/signup', data={
        'username': 'usera',
        'email': 'usera@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    user_a = db.get_user_by_username("usera")
    db.save_search(
        query="dentists",
        city="Chicago",
        results_count=10,
        leads_count=5,
        user_id=user_a["id"]
    )
    
    # Verify User A can see their own history
    client.post('/login', data={'email': 'usera@example.com', 'password': 'password123'})
    resp_a = client.get('/api/history')
    assert resp_a.status_code == 200
    assert len(resp_a.json["history"]) == 1
    assert resp_a.json["history"][0]["query"] == "dentists"
    
    # Log out User A
    client.get('/logout')
    
    # 2. Create User B
    client.post('/signup', data={
        'username': 'userb',
        'email': 'userb@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    user_b = db.get_user_by_username("userb")
    
    # Verify User B sees empty history
    client.post('/login', data={'email': 'userb@example.com', 'password': 'password123'})
    resp_b = client.get('/api/history')
    assert resp_b.status_code == 200
    assert len(resp_b.json["history"]) == 0
    
    # Verify DB helper checks
    assert len(db.get_search_history(user_id=user_b["id"])) == 0
    assert len(db.get_search_history(user_id=None)) == 0


def test_lead_ownership_constraints(client, db):
    """Verify User B cannot view, delete, schedule reminders, or change stage for User A's leads."""
    # Create User A
    client.post('/signup', data={'username': 'usera', 'email': 'usera@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_a = db.get_user_by_username("usera")
    
    # Create User B
    client.post('/signup', data={'username': 'userb', 'email': 'userb@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_b = db.get_user_by_username("userb")
    
    # Save a lead for User A
    lead_a = Lead(name="User A Salon", place_id="salon_a", city="Austin", website="https://usera-salon.com")
    db.save_leads([lead_a], user_a["id"])
    saved_lead = db.get_all_leads(user_id=user_a["id"])[0]
    lead_id = saved_lead["id"]
    
    # Log in as User B
    client.post('/login', data={'email': 'userb@example.com', 'password': 'password123'})
    
    # 1. Try to fetch User A's lead details (via get_lead_by_id DB helper with User B's ID)
    assert db.get_lead_by_id(lead_id, user_id=user_b["id"]) is None
    
    # 2. Try to update pipeline stage
    resp = client.post(f'/api/leads/{lead_id}/pipeline', json={"stage": "PITCHED"})
    assert resp.status_code == 500  # Fails database update due to user_id filter mismatch
    
    # 3. Try to schedule reminder
    resp = client.post(f'/api/leads/{lead_id}/schedule-reminder', json={"days": 5})
    assert resp.status_code == 500  # Fails database update
    
    # 4. Try to dismiss reminder
    resp = client.post(f'/api/leads/{lead_id}/dismiss-reminder')
    assert resp.status_code == 500  # Fails database update
    
    # 5. Try on-demand scan/audit actions (should return 404)
    resp = client.post(f'/api/leads/{lead_id}/scan-socials')
    assert resp.status_code == 404
    
    resp = client.post(f'/api/leads/{lead_id}/scan-email')
    assert resp.status_code == 404
    
    resp = client.post(f'/api/leads/{lead_id}/audit')
    assert resp.status_code == 404


def test_outreach_logs_isolation(client, db):
    """Verify that outreach logs of User A's leads cannot be accessed by User B."""
    # Create User A
    client.post('/signup', data={'username': 'usera', 'email': 'usera@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_a = db.get_user_by_username("usera")
    
    # Create User B
    client.post('/signup', data={'username': 'userb', 'email': 'userb@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_b = db.get_user_by_username("userb")
    
    # Save a lead for User A
    lead_a = Lead(name="User A Gym", place_id="gym_a", city="Austin")
    db.save_leads([lead_a], user_a["id"])
    saved_lead = db.get_all_leads(user_id=user_a["id"])[0]
    lead_id = saved_lead["id"]
    
    # Create an outreach log for User A's lead
    db.log_message(lead_id, template="cold_email", message="Hello from User A", user_id=user_a["id"])
    
    # Log in as User B
    client.post('/login', data={'email': 'userb@example.com', 'password': 'password123'})
    
    # Query outreach logs via API
    resp = client.get(f'/api/leads/{lead_id}/outreach-logs')
    assert resp.status_code == 404
    
    # Query logs directly via DB helper with User B's ID
    logs = db.get_lead_outreach_logs(lead_id, user_b["id"])
    assert len(logs) == 0


def test_send_smtp_email_isolation(client, db):
    """Verify User B cannot send outreach email or log message for User A's lead."""
    # Create User A
    client.post('/signup', data={'username': 'usera', 'email': 'usera@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_a = db.get_user_by_username("usera")
    
    # Create User B
    client.post('/signup', data={'username': 'userb', 'email': 'userb@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_b = db.get_user_by_username("userb")
    
    # Save a lead for User A
    lead_a = Lead(name="User A Shop", place_id="shop_a", city="Austin")
    db.save_leads([lead_a], user_a["id"])
    saved_lead = db.get_all_leads(user_id=user_a["id"])[0]
    lead_id = saved_lead["id"]
    
    # Log in as User B
    client.post('/login', data={'email': 'userb@example.com', 'password': 'password123'})
    
    # Try sending SMTP email targeting User A's lead
    smtp_payload = {
        "to_email": "target@example.com",
        "subject": "Test Outreach",
        "body": "Hi there",
        "smtp_config": {
            "host": "smtp.gmail.com",
            "port": 587,
            "email": "userb@example.com",
            "password": "somepassword",
            "use_ssl": False
        },
        "lead_id": lead_id
    }
    resp = client.post('/api/outreach/send-smtp-email', json=smtp_payload)
    assert resp.status_code == 404
    
    # Verify no message log is generated for User A's lead under User B's id
    logs = db.get_lead_outreach_logs(lead_id, user_b["id"])
    assert len(logs) == 0


def test_deactivated_session_middleware(client, db):
    """Verify that an active user session is cleared immediately if the account is deactivated in DB."""
    # 1. Sign up and log in
    client.post('/signup', data={'username': 'activeuser', 'email': 'active@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    client.post('/login', data={'email': 'active@example.com', 'password': 'password123'})
    
    # Verify active session works
    resp = client.get('/api/leads')
    assert resp.status_code == 200
    
    user = db.get_user_by_username("activeuser")
    
    # 2. Deactivate the user in DB
    db.toggle_user_active(user["id"], False)
    
    # 3. Access again - middleware should detect inactive state, clear session, and block with 401
    resp2 = client.get('/api/leads')
    assert resp2.status_code == 401
    
    # Also verify redirect for non-API routes
    resp3 = client.get('/admin', follow_redirects=False)
    assert resp3.status_code == 302
    assert "/login" in resp3.headers.get("Location", "")


def test_cross_tenant_whatsapp_generate(client, db):
    """Verify User B cannot log WhatsApp outreach for User A's lead."""
    # Create User A
    client.post('/signup', data={'username': 'usera', 'email': 'usera@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_a = db.get_user_by_username("usera")
    
    # Create User B
    client.post('/signup', data={'username': 'userb', 'email': 'userb@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user_b = db.get_user_by_username("userb")
    
    # Save a lead for User A
    lead_a = Lead(name="User A Salon", place_id="salon_a", city="Austin")
    db.save_leads([lead_a], user_a["id"])
    saved_lead = db.get_all_leads(user_id=user_a["id"])[0]
    lead_id = saved_lead["id"]
    
    # Log in as User B
    client.post('/login', data={'email': 'userb@example.com', 'password': 'password123'})
    
    # Try generating a WhatsApp link using User A's lead_id
    payload = {
        "phone": "+15555555555",
        "template": "website_pitch",
        "custom_message": "test",
        "lead": {"id": lead_id, "name": "User A Salon"}
    }
    resp = client.post('/api/whatsapp/generate', json=payload)
    assert resp.status_code == 404
    
    # Check no message log exists under User B for this lead
    logs = db.get_lead_outreach_logs(lead_id, user_b["id"])
    assert len(logs) == 0


def test_otp_brute_force_prevention(client, db):
    """Verify that 5 failed OTP verification attempts delete/invalidate the reset token in DB."""
    # Create a user
    client.post('/signup', data={'username': 'otpuser', 'email': 'otp@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    
    # Mock system SMTP setup to bypass config checks
    with patch("utils.email_sender.is_smtp_configured", return_value=True), \
         patch("utils.email_sender.send_otp_email") as mock_send_email:
        # Request password reset OTP
        client.post('/forgot-password', data={'email': 'otp@example.com'})
        
        # Verify an OTP record is created in database
        conn = db._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM password_resets WHERE email = 'otp@example.com';")
            assert cursor.fetchone()[0] == 1
        finally:
            db._release_connection(conn)
            
        # Submit invalid OTP 4 times
        for _ in range(4):
            resp = client.post('/verify-otp', data={'otp': '000000'})
            assert resp.status_code == 200  # returns 200 to show template with invalid OTP flash
            
        # Confirm OTP still exists in DB after 4 failed attempts
        conn = db._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM password_resets WHERE email = 'otp@example.com';")
            assert cursor.fetchone()[0] == 1
        finally:
            db._release_connection(conn)
            
        # 5th failed attempt
        resp5 = client.post('/verify-otp', data={'otp': '000000'}, follow_redirects=True)
        # Should redirect to forgot-password page
        assert b"Too many failed attempts" in resp5.data
        
        # Verify OTP record has been deleted in database
        conn = db._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM password_resets WHERE email = 'otp@example.com';")
            assert cursor.fetchone()[0] == 0
        finally:
            db._release_connection(conn)


def test_persistent_encryption_fallback(db):
    """Verify that omitting FLASK_SECRET_KEY environment variable uses persistent DB key fallback, yielding stable encryption."""
    import os
    
    raw_pass = "secret_smtp_config_password_123"
    
    # 1. Mock FLASK_SECRET_KEY is absent from env
    with patch.dict(os.environ, {}, clear=True), patch("os.getenv", return_value=None):
        # Clean existing system settings key for fresh generation
        conn = db._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM system_settings WHERE key = 'credential_encryption_secret';")
            conn.commit()
        finally:
            db._release_connection(conn)
            
        # Encrypt password
        encrypted1 = db._encrypt_password(raw_pass)
        assert encrypted1 != raw_pass
        
        # Verify DB key was created
        system_secret = db.get_system_setting("credential_encryption_secret")
        assert len(system_secret) > 0
        
        # Verify decryption works
        decrypted1 = db._decrypt_password(encrypted1)
        assert decrypted1 == raw_pass
        
        # Mock server restart (DB key is kept)
        decrypted2 = db._decrypt_password(encrypted1)
        assert decrypted2 == raw_pass

