# pyrefly: ignore [missing-import]
import pytest
from collectors.base_collector import Lead
from datetime import datetime, timedelta

def test_imap_and_smtp_db_accessors(db):
    """Verify IMAP and SMTP configurations can be saved, encrypted, and retrieved securely."""
    # Create test user
    db.create_user("testuser", "testuser@example.com", "password123")
    user = db.get_user_by_email("testuser@example.com")
    user_id = user["id"]

    # 1. IMAP Settings
    success = db.save_imap_settings(
        user_id=user_id,
        host="imap.example.com",
        port=993,
        email="testuser@example.com",
        password_raw="secretapppassword",
        use_ssl=True
    )
    assert success is True

    imap_settings = db.get_imap_settings(user_id)
    assert imap_settings is not None
    assert imap_settings["host"] == "imap.example.com"
    assert imap_settings["port"] == 993
    assert imap_settings["email"] == "testuser@example.com"
    assert imap_settings["password"] == "secretapppassword"  # Decrypted successfully
    assert imap_settings["use_ssl"] is True

    # 2. SMTP Settings
    success_smtp = db.save_smtp_settings(
        user_id=user_id,
        host="smtp.example.com",
        port=465,
        email="testuser@example.com",
        password_raw="secretapppassword_smtp",
        use_ssl=True
    )
    assert success_smtp is True

    smtp_settings = db.get_smtp_settings(user_id)
    assert smtp_settings is not None
    assert smtp_settings["host"] == "smtp.example.com"
    assert smtp_settings["port"] == 465
    assert smtp_settings["email"] == "testuser@example.com"
    assert smtp_settings["password"] == "secretapppassword_smtp"  # Decrypted successfully
    assert smtp_settings["use_ssl"] is True


def test_drip_configurations_db_accessors(db):
    """Verify follow-up drip campaign settings can be saved and retrieved correctly."""
    # Create test user
    db.create_user("testuser", "testuser@example.com", "password123")
    user = db.get_user_by_email("testuser@example.com")
    user_id = user["id"]

    success = db.save_drip_config(
        user_id=user_id,
        delay_days=5,
        max_followups=3,
        followup_subject="Follow up regarding proposal",
        followup_template="Hi {business_name}, checking in...",
        is_enabled=True
    )
    assert success is True

    config = db.get_drip_config(user_id)
    assert config is not None
    assert config["delay_days"] == 5
    assert config["max_followups"] == 3
    assert config["followup_subject"] == "Follow up regarding proposal"
    assert config["followup_template"] == "Hi {business_name}, checking in..."
    assert config["is_enabled"] is True


def test_imap_reply_tracking_stage_transition(db):
    """Verify that logging an inbound reply advances pipeline stage to REPLIED and records log."""
    db.create_user("testuser", "testuser@example.com", "password123")
    user = db.get_user_by_email("testuser@example.com")
    user_id = user["id"]

    # Insert a lead in CONTACTED/PITCHED stage
    lead = Lead(name="Local Store", place_id="place_store", email="store@example.com", city="Bhopal")
    db.save_leads([lead], user_id)
    
    saved_leads = db.get_all_leads(user_id=user_id)
    lead_id = saved_leads[0]["id"]
    db.update_lead_pipeline_stage(lead_id, "PITCHED", user_id=user_id)

    # Assert initial stage
    lead_db = db.get_lead_by_id(lead_id, user_id=user_id)
    assert lead_db["pipeline_stage"] == "PITCHED"

    # Record inbound reply
    db.record_inbound_reply(
        lead_id=lead_id,
        user_id=user_id,
        sender_email="store@example.com",
        reply_text="I am interested, tell me more!"
    )

    # Assert updated pipeline stage and message log existence
    lead_updated = db.get_lead_by_id(lead_id, user_id=user_id)
    assert lead_updated["pipeline_stage"] == "REPLIED"
    assert lead_updated["contacted"] is True

    logs = db.get_lead_outreach_logs(lead_id, user_id=user_id)
    assert len(logs) == 1
    assert logs[0]["is_reply"] is True
    assert logs[0]["reply_body"] == "I am interested, tell me more!"


def test_drip_scheduler_targeting_query(db):
    """Verify database targeting logic selects unengaged pitched leads needing follow-up drips."""
    db.create_user("testuser", "testuser@example.com", "password123")
    user = db.get_user_by_email("testuser@example.com")
    user_id = user["id"]

    # Lead 1: PITCHED, sequence active, last followup/contact date is old (3 days ago) -> TARGET
    lead_target = Lead(name="Target Salon", place_id="place_target", email="target@example.com", city="Bhopal")
    
    # Lead 2: Stage is INTERESTED -> EXCLUDE
    lead_interested = Lead(name="Engaged Gym", place_id="place_engaged", email="engaged@example.com", city="Bhopal")
    
    # Lead 3: Drip sequence inactive -> EXCLUDE
    lead_inactive = Lead(name="Inactive Shop", place_id="place_inactive", email="inactive@example.com", city="Bhopal")

    db.save_leads([lead_target, lead_interested, lead_inactive], user_id)

    # Query leads back to set timestamps and stages
    leads_db = db.get_all_leads(user_id=user_id)
    id_target = next(l["id"] for l in leads_db if l["place_id"] == "place_target")
    id_engaged = next(l["id"] for l in leads_db if l["place_id"] == "place_engaged")
    id_inactive = next(l["id"] for l in leads_db if l["place_id"] == "place_inactive")

    # Target settings
    db.update_lead_pipeline_stage(id_target, "PITCHED", user_id=user_id)
    # Mock last contact date to 4 days ago
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leads 
        SET contacted = TRUE,
            contact_date = CURRENT_TIMESTAMP - INTERVAL '4 days',
            last_followup_date = NULL,
            followup_count = 0,
            drip_sequence_active = TRUE
        WHERE id = %s
    """, (id_target,))
    
    # Engaged settings
    db.update_lead_pipeline_stage(id_engaged, "INTERESTED", user_id=user_id)
    cursor.execute("""
        UPDATE leads 
        SET contacted = TRUE,
            contact_date = CURRENT_TIMESTAMP - INTERVAL '4 days'
        WHERE id = %s
    """, (id_engaged,))

    # Inactive settings
    db.update_lead_pipeline_stage(id_inactive, "PITCHED", user_id=user_id)
    cursor.execute("""
        UPDATE leads 
        SET contacted = TRUE,
            contact_date = CURRENT_TIMESTAMP - INTERVAL '4 days',
            drip_sequence_active = FALSE
        WHERE id = %s
    """, (id_inactive,))

    conn.commit()
    db._release_connection(conn)

    # Perform the database query that the drip sequencer uses
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email
        FROM leads
        WHERE user_id = %s 
          AND email IS NOT NULL AND email != ''
          AND contacted = TRUE
          AND pipeline_stage = 'PITCHED'
          AND drip_sequence_active = TRUE
          AND followup_count < %s
          AND COALESCE(last_followup_date, contact_date) <= CURRENT_TIMESTAMP - (INTERVAL '1 day' * %s);
    """, (user_id, 2, 3))
    targets = cursor.fetchall()
    db._release_connection(conn)

    assert len(targets) == 1
    assert targets[0]["id"] == id_target
    assert targets[0]["name"] == "Target Salon"


def test_analytics_api_endpoint(auth_client, db):
    """Verify that GET /api/stats/analytics computes and returns structured funnel and telemetry rates."""
    # Check stats for user (auth_client creates user: test@example.com)
    user = db.get_user_by_email("test@example.com")
    user_id = user["id"]

    # Seed some dummy leads and message logs
    lead1 = Lead(name="Store 1", place_id="place_store1", email="store1@example.com", city="Bhopal")
    lead2 = Lead(name="Store 2", place_id="place_store2", email="store2@example.com", city="Bhopal")
    db.save_leads([lead1, lead2], user_id)

    leads_db = db.get_all_leads(user_id=user_id)
    id1 = leads_db[0]["id"]
    id2 = leads_db[1]["id"]

    # Lead 1: Pitched, Opened and Clicked
    db.update_lead_pipeline_stage(id1, "INTERESTED", user_id=user_id)
    log_id1 = db.log_message(id1, "cold_email", "Hello proposals", user_id)
    
    # Lead 2: Pitched, Opened only
    db.update_lead_pipeline_stage(id2, "PITCHED", user_id=user_id)
    log_id2 = db.log_message(id2, "cold_email", "Hello proposals 2", user_id)

    # Simulate opens and clicks in database
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE message_log SET opened = TRUE, open_count = 1 WHERE id IN (%s, %s)", (log_id1, log_id2))
    cursor.execute("UPDATE message_log SET clicked = TRUE, click_count = 1 WHERE id = %s", (log_id1,))
    conn.commit()
    db._release_connection(conn)

    # Perform GET /api/stats/analytics
    response = auth_client.get('/api/stats/analytics')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"] is True
    assert "funnel" in data
    assert "timeline" in data
    assert "ratios" in data

    # Assert funnel counts
    funnel = data["funnel"]
    assert funnel["scouted"] == 2
    assert funnel["pitched"] == 2
    assert funnel["opened"] == 2
    assert funnel["clicked"] == 1
    assert funnel["closed"] == 0

    # Assert engagement ratios
    ratios = data["ratios"]
    assert ratios["total_sent"] == 2
    assert ratios["open_rate"] == 100.0
    assert ratios["click_rate"] == 50.0
    assert ratios["reply_rate"] == 0.0
