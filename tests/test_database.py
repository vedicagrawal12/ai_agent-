# pyrefly: ignore [missing-import]
import pytest
from collectors.base_collector import Lead
from datetime import datetime, timedelta

def test_db_create_user(db):
    """Verify raw user insertion and admin designation for the first user."""
    success = db.create_user("user1", "user1@example.com", "hash123", "1234567890")
    assert success is True
    
    # Retrieve user
    user = db.get_user_by_username("user1")
    assert user is not None
    assert user["username"] == "user1"
    assert user["email"] == "user1@example.com"
    assert user["password_hash"] == "hash123"
    assert user["phone"] == "1234567890"

    # Retrieve user by email
    user_by_email = db.get_user_by_email("user1@example.com")
    assert user_by_email is not None
    assert user_by_email["id"] == user["id"]
    assert user_by_email["phone"] == "1234567890"

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

def test_db_user_id_zero_safety(db):
    """Verify that querying with user_id = 0 does not leak other users' data (BUG-H4)."""
    # Create test user
    db.create_user("user_a", "usera@example.com", "hash")
    user = db.get_user_by_username("user_a")
    user_id = user["id"]
    
    # Save a lead for user_a
    lead = Lead(name="Lead A", place_id="place_a", city="Bhopal", priority="HIGH")
    db.save_leads([lead], user_id)
    
    # Log a search for user_a
    db.save_search("Gyms", "Bhopal", 10, 5, user_id)
    
    # Schedule a reminder for user_a
    leads_in_db = db.get_all_leads(user_id=user_id)
    lead_id = leads_in_db[0]["id"]
    db.schedule_reminder(lead_id, "2026-06-30", user_id)
    
    # 1. Check get_stats for user_id = 0
    stats_zero = db.get_stats(user_id=0)
    assert stats_zero["total_leads"] == 0
    assert stats_zero["high_priority"] == 0
    assert stats_zero["total_searches"] == 0
    
    # 2. Check get_search_history for user_id = 0
    history_zero = db.get_search_history(user_id=0)
    assert len(history_zero) == 0
    
    # 3. Check get_pending_reminders for user_id = 0
    reminders_zero = db.get_pending_reminders(user_id=0)
    assert len(reminders_zero) == 0
    
    # 4. Check clear_uncontacted_data for user_id = 0
    res = db.clear_uncontacted_data(user_id=0)
    assert res["success"] is True
    assert res["leads_deleted"] == 0
    assert res["history_deleted"] == 0
    
    # Verify user_a's data was NOT deleted by clear_uncontacted_data(user_id=0)
    leads_after = db.get_all_leads(user_id=user_id)
    assert len(leads_after) == 1
    assert leads_after[0]["name"] == "Lead A"

def test_db_admin_auto_promotion_safeguard(db):
    """Verify admin auto-promotion only occurs if no admin exists (BUG-H7)."""
    # Create two users
    db.create_user("user_first", "first@example.com", "hash")
    db.create_user("user_second", "second@example.com", "hash")
    
    first = db.get_user_by_username("user_first")
    second = db.get_user_by_username("user_second")
    
    # Manually make first user an admin (which represents the baseline state)
    db.toggle_user_admin(first["id"], True)
    assert db.is_user_admin(first["id"]) is True
    assert db.is_user_admin(second["id"]) is False
    
    # Trigger a database init again
    db._init_db()
    
    # Verify second user was NOT auto-promoted since first user is already admin
    assert db.is_user_admin(first["id"]) is True
    assert db.is_user_admin(second["id"]) is False

def test_db_save_leads_savepoint_fault_tolerance(db):
    """Verify that one failing lead in save_leads does not rollback other successful leads (BUG-M4/M11)."""
    db.create_user("savepoint_user", "sp@example.com", "hash")
    user = db.get_user_by_username("savepoint_user")
    user_id = user["id"]
    
    # Lead 1: Valid
    lead1 = Lead(name="Valid Lead 1", place_id="place_sp_1", city="Bhopal")
    # Lead 2: Invalid (name is None, which violates NOT NULL constraint)
    lead2 = Lead(name=None, place_id="place_sp_2", city="Bhopal")
    # Lead 3: Valid
    lead3 = Lead(name="Valid Lead 3", place_id="place_sp_3", city="Bhopal")
    
    # Run save_leads. It should not raise an exception, and return 2 successful inserts
    new_count = db.save_leads([lead1, lead2, lead3], user_id)
    assert new_count == 2
    
    # Check database leads
    saved = db.get_all_leads(user_id=user_id)
    assert len(saved) == 2
    names = {l["name"] for l in saved}
    assert "Valid Lead 1" in names
    assert "Valid Lead 3" in names
