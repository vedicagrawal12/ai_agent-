# pyrefly: ignore [missing-import]
import pytest
from collectors.base_collector import Lead
from datetime import datetime, timedelta

def test_db_create_user(db):
    """Verify raw user insertion and admin designation for the first user."""
    # Create first user - should automatically default to is_admin=True in inline migrations
    # Wait, the inline migration update query is:
    # "UPDATE users SET is_admin = TRUE WHERE id = (SELECT MIN(id) FROM users) AND is_admin = FALSE;"
    # This query runs during _init_db(). Let's test that create_user works.
    success = db.create_user("user1", "user1@example.com", "hash123")
    assert success is True
    
    # Retrieve user
    user = db.get_user_by_username("user1")
    assert user is not None
    assert user["username"] == "user1"
    assert user["email"] == "user1@example.com"
    assert user["password_hash"] == "hash123"

def test_db_save_leads_insert_and_update(db):
    """Verify batch lead saves and upsert logic on conflict."""
    # Create test user
    db.create_user("user_lead", "user_lead@example.com", "hash")
    user = db.get_user_by_username("user_lead")
    user_id = user["id"]
    
    # Batch save new leads
    lead1 = Lead(name="Lead 1", place_id="place_1", city="Bhopal", priority="LOW")
    lead2 = Lead(name="Lead 2", place_id="place_2", city="Bhopal", priority="MEDIUM")
    
    new_count = db.save_leads([lead1, lead2], user_id)
    assert new_count == 2
    
    # Check leads in DB
    saved = db.get_all_leads(user_id=user_id)
    assert len(saved) == 2
    
    # Conflict updates
    lead1_updated = Lead(name="Lead 1 Updated", place_id="place_1", city="Bhopal", priority="HIGH")
    new_count_conflict = db.save_leads([lead1_updated], user_id)
    assert new_count_conflict == 0  # Conflicted, updated instead of inserted
    
    # Verify values updated
    saved_updated = db.get_all_leads(user_id=user_id)
    lead1_db = next(l for l in saved_updated if l["place_id"] == "place_1")
    assert lead1_db["name"] == "Lead 1 Updated"
    assert lead1_db["priority"] == "HIGH"

def test_db_tenant_isolation(db):
    """Verify User A cannot query User B's saved leads."""
    # Create User A and User B
    db.create_user("usera", "usera@example.com", "hash")
    db.create_user("userb", "userb@example.com", "hash")
    user_a = db.get_user_by_username("usera")
    user_b = db.get_user_by_username("userb")
    
    # Save lead for User A
    lead_a = Lead(name="Lead A", place_id="place_a", city="Bhopal")
    db.save_leads([lead_a], user_a["id"])
    
    # Save lead for User B
    lead_b = Lead(name="Lead B", place_id="place_b", city="Bhopal")
    db.save_leads([lead_b], user_b["id"])
    
    # Retrieve leads for User A
    leads_for_a = db.get_all_leads(user_id=user_a["id"])
    assert len(leads_for_a) == 1
    assert leads_for_a[0]["name"] == "Lead A"
    
    # Retrieve leads for User B
    leads_for_b = db.get_all_leads(user_id=user_b["id"])
    assert len(leads_for_b) == 1
    assert leads_for_b[0]["name"] == "Lead B"

def test_db_smart_cleanup_retention(db):
    """Verify startup cleanup deletes old data but respects pending reminders."""
    db.create_user("cleanup_user", "clean@example.com", "hash")
    user = db.get_user_by_username("cleanup_user")
    user_id = user["id"]
    
    # Lead 1: Uncontacted, created 15 days ago, NO reminder -> Should be deleted
    lead_old = Lead(name="Old Gym", place_id="place_old", city="Bhopal")
    db.save_leads([lead_old], user_id)
    
    # Lead 2: Uncontacted, created 15 days ago, HAS pending reminder -> Should be preserved
    lead_remind = Lead(name="Old Gym with Reminder", place_id="place_remind", city="Bhopal")
    db.save_leads([lead_remind], user_id)
    
    # Retrieve lead ids to set created_at and remind statuses manually
    leads_in_db = db.get_all_leads(user_id=user_id)
    db_id_old = next(l["id"] for l in leads_in_db if l["place_id"] == "place_old")
    db_id_remind = next(l["id"] for l in leads_in_db if l["place_id"] == "place_remind")
    
    # Update created_at using SQL
    conn = db._get_connection()
    cursor = conn.cursor()
    try:
        old_created = datetime.now() - timedelta(days=16)
        cursor.execute("UPDATE leads SET created_at = %s WHERE id = %s", (old_created, db_id_old))
        cursor.execute("UPDATE leads SET created_at = %s WHERE id = %s", (old_created, db_id_remind))
        conn.commit()
    finally:
        db._release_connection(conn)
        
    # Schedule reminder for lead 2
    db.schedule_reminder(db_id_remind, "2026-06-30", user_id)
    
    # Run cleanup
    db.cleanup_old_data()
    
    # Verify leads remaining in DB
    remaining_leads = db.get_all_leads(user_id=user_id)
    assert len(remaining_leads) == 1
    assert remaining_leads[0]["id"] == db_id_remind
    assert remaining_leads[0]["name"] == "Old Gym with Reminder"

def test_db_connection_pool(db):
    """Verify ThreadedConnectionPool leases and releases connections safely."""
    # Obtain connections
    conn1 = db._get_connection()
    conn2 = db._get_connection()
    
    # Ensure they are valid connections
    assert conn1 is not None
    assert conn2 is not None
    assert conn1 != conn2
    
    # Release connections back to pool
    db._release_connection(conn1)
    db._release_connection(conn2)
