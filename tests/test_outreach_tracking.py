import pytest
import urllib.parse
from unittest.mock import patch, MagicMock
from collectors.base_collector import Lead
from io import BytesIO

def test_smtp_link_wrapping_and_tracking(auth_client, db):
    """Verify SMTP email link wrapping, pixel injection, and sending mock."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Create test lead
    lead = Lead(name="Test Tracker Gym", place_id="place_track_1", city="Bhopal", email="recipient@gym.com")
    db.save_leads([lead], user_id)
    saved_lead = db.get_all_leads(user_id=user_id)[0]
    
    # Body containing a mockup and audit URL to track
    email_body = "Hello! Check out your mockup here: http://example.com/mockup. Also see your SEO report: http://example.com/audit."
    
    # Prepare SMTP configuration payload
    smtp_payload = {
        "to_email": "recipient@gym.com",
        "subject": "Mockup and SEO Audit for Test Tracker Gym",
        "body": email_body,
        "lead_id": saved_lead["id"],
        "smtp_config": {
            "host": "smtp.gmail.com",
            "port": 587,
            "email": "sender@gmail.com",
            "password": "securepassword",
            "use_ssl": False
        }
    }
    
    # Mock SMTP to prevent actual network dispatch
    with patch("smtplib.SMTP") as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value = mock_instance
        
        # Trigger sending
        resp = auth_client.post('/api/outreach/send-smtp-email', json=smtp_payload)
        
        # Assert API response
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert "Email successfully dispatched" in resp.json["message"]
        
        # Verify SMTP server was logged into and sendmail was called
        mock_instance.login.assert_called_once_with("sender@gmail.com", "securepassword")
        assert mock_instance.sendmail.called
        
        # Inspect sent email components
        call_args = mock_instance.sendmail.call_args[0]
        sender_used = call_args[0]
        recipient_used = call_args[1]
        msg_str = call_args[2]
        
        assert sender_used == "sender@gmail.com"
        assert recipient_used == ["recipient@gym.com"]
        
        # Verify link wrapping in html part
        import email
        parsed_msg = email.message_from_string(msg_str)
        html_part = None
        for part in parsed_msg.walk():
            if part.get_content_type() == "text/html":
                html_part = part.get_payload(decode=True).decode('utf-8')
                
        assert html_part is not None
        assert "http://localhost/api/track/click/" in html_part
        assert "dest=http%3A//example.com/mockup" in html_part
        assert "dest=http%3A//example.com/audit" in html_part
        assert "http://localhost/api/track/open/" in html_part
        
        # Verify message log was saved in database
        logs = db.get_lead_outreach_logs(saved_lead["id"], user_id)
        assert len(logs) == 1
        log = logs[0]
        assert log["template_used"] == "cold_email"
        assert email_body in log["message_sent"] or "dest=http%3A//example.com/mockup" in log["message_sent"]
        assert log["opened"] is False
        assert log["clicked"] is False

def test_open_tracking(auth_client, db):
    """Verify open tracking sets status, increments count, and returns GIF."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Create test lead & log a message
    lead = Lead(name="Test Open Gym", place_id="place_track_2", city="Bhopal")
    db.save_leads([lead], user_id)
    saved_lead = db.get_all_leads(user_id=user_id)[0]
    
    log_id = db.log_message(saved_lead["id"], "cold_email", "Message content", user_id)
    assert log_id > 0
    
    # 1. First track open
    resp = auth_client.get(f'/api/track/open/{log_id}')
    assert resp.status_code == 200
    assert resp.mimetype == 'image/gif'
    
    # Verify transparent GIF bytes
    transparent_gif_start = b'GIF89a'
    assert resp.data.startswith(transparent_gif_start)
    
    # Verify DB state
    logs = db.get_lead_outreach_logs(saved_lead["id"], user_id)
    assert len(logs) == 1
    assert logs[0]["opened"] is True
    assert logs[0]["open_count"] == 1
    assert logs[0]["opened_at"] is not None
    
    # 2. Second track open
    resp2 = auth_client.get(f'/api/track/open/{log_id}')
    assert resp2.status_code == 200
    
    logs2 = db.get_lead_outreach_logs(saved_lead["id"], user_id)
    assert logs2[0]["open_count"] == 2

def test_click_tracking_and_pipeline_advancement(auth_client, db):
    """Verify click tracking logs destination, advances pipeline, and redirects."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Create test lead & log a message
    lead = Lead(name="Test Click Gym", place_id="place_track_3", city="Bhopal")
    db.save_leads([lead], user_id)
    saved_lead = db.get_all_leads(user_id=user_id)[0]
    assert saved_lead["pipeline_stage"] == "NEW"
    
    log_id = db.log_message(saved_lead["id"], "cold_email", "Message content", user_id)
    assert log_id > 0
    
    dest_url = "http://example.com/mockup?client=123"
    encoded_dest = urllib.parse.quote(dest_url)
    
    # Trigger link click redirect
    resp = auth_client.get(f'/api/track/click/{log_id}?dest={encoded_dest}')
    
    # Check redirect status and location
    assert resp.status_code == 302
    assert resp.location == dest_url
    
    # Verify DB click logs
    logs = db.get_lead_outreach_logs(saved_lead["id"], user_id)
    assert len(logs) == 1
    assert logs[0]["clicked"] is True
    assert logs[0]["click_count"] == 1
    assert logs[0]["clicked_at"] is not None
    assert logs[0]["clicked_links"] == dest_url
    
    # Verify lead pipeline was bumped automatically to INTERESTED
    updated_lead = db.get_lead_by_id(saved_lead["id"], user_id)
    assert updated_lead["pipeline_stage"] == "INTERESTED"

def test_get_outreach_logs_endpoint(auth_client, db):
    """Verify get_lead_outreach_logs API endpoint works correctly."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    lead = Lead(name="Test Logs Gym", place_id="place_track_4", city="Bhopal")
    db.save_leads([lead], user_id)
    saved_lead = db.get_all_leads(user_id=user_id)[0]
    
    # Check empty history
    resp = auth_client.get(f'/api/leads/{saved_lead["id"]}/outreach-logs')
    assert resp.status_code == 200
    assert resp.json == []
    
    # Add a log
    db.log_message(saved_lead["id"], "cold_email", "Hello testing!", user_id)
    
    # Check populated history
    resp2 = auth_client.get(f'/api/leads/{saved_lead["id"]}/outreach-logs')
    assert resp2.status_code == 200
    assert len(resp2.json) == 1
    assert resp2.json[0]["template_used"] == "cold_email"
    assert resp2.json[0]["message_sent"] == "Hello testing!"
