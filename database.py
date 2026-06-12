import psycopg2
import psycopg2.extras
from psycopg2 import pool
import json
import os
import logging
import threading
from datetime import datetime
from typing import List, Optional, Dict
from collectors.base_collector import Lead
from constants import CLEANUP_UNCONTACTED_DAYS, CLEANUP_IGNORED_DAYS, CLEANUP_HISTORY_DAYS


class Database:
    """PostgreSQL database manager for lead storage."""

    # Class-level connection pool
    _pool = None
    _pool_dsn = None
    _pool_lock = threading.Lock()

    # Class-level flag to prevent double cleanup in Flask debug mode (reloader runs __init__ twice)
    _cleanup_done = False
    _cleanup_lock = threading.Lock()  # BUG-M8 fix: Thread-safe cleanup flag

    def __init__(self, db_url: str = None):
        """Initialize database connection and create tables if needed."""
        if not db_url:
            db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/leadhunter_db")
        # Handle case where DATABASE_URL still has the placeholder
        if "YOUR_POSTGRES_PASSWORD" in db_url:
            logging.warning("[Database] DATABASE_URL contains placeholder password. Falling back to default 'postgres' password.")
            db_url = db_url.replace("YOUR_POSTGRES_PASSWORD", "postgres")
        self.db_url = db_url

        # Initialize thread-safe connection pool once
        with Database._pool_lock:
            # If the database URL has changed, close the old pool and allow recreation
            if Database._pool is not None and Database._pool_dsn != self.db_url:
                logging.info("[Database] Database URL changed. Re-creating connection pool...")
                try:
                    Database._pool.closeall()
                except Exception as close_err:
                    logging.error(f"[Database] Error closing connection pool: {close_err}")
                Database._pool = None

            if Database._pool is None:
                logging.info(f"[Database] Initializing connection pool with URL: {self.db_url}...")
                Database._pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    dsn=self.db_url,
                    cursor_factory=psycopg2.extras.DictCursor
                )
                Database._pool_dsn = self.db_url

        self._init_db()

    def _get_connection(self):
        """Get a database connection from the connection pool."""
        return Database._pool.getconn()

    def _release_connection(self, conn):
        """Release a database connection back to the pool."""
        if conn:
            Database._pool.putconn(conn)

    def close(self):
        """Close the database connection pool."""
        with Database._pool_lock:
            if Database._pool is not None:
                try:
                    Database._pool.closeall()
                except Exception:
                    pass
                Database._pool = None
                Database._pool_dsn = None

    def _init_db(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        try:
            def run_query(query, params=None):
                cursor = conn.cursor()
                try:
                    cursor.execute(query, params)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logging.debug(f"[Database Init] Query skipped/failed: {query}. Error: {e}")

            # Users table (created if not exists, with password_hash as TEXT, email column, and phone column)
            run_query("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    phone VARCHAR(50) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Safe migration: ensure existing password_hash column is TYPE TEXT, email, phone, is_admin, and is_active columns exist
            run_query("ALTER TABLE users ALTER COLUMN password_hash TYPE TEXT;")
            run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) DEFAULT '';")
            run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50) DEFAULT '';")
            run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
            run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
            
            # Migrate duplicate/empty emails to ensure UNIQUE and NOT NULL constraint can be safely applied
            run_query("UPDATE users SET email = username || '@example.com' WHERE email IS NULL OR email = '' OR email = 'placeholder@example.com';")
            run_query("ALTER TABLE users ALTER COLUMN email SET NOT NULL;")
            run_query("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key;")
            run_query("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_email_key') THEN
                        ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
                    END IF;
                END
                $$;
            """)
            run_query("UPDATE users SET is_admin = TRUE WHERE id = (SELECT MIN(id) FROM users) AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin = TRUE);")

            # Leads table
            run_query("""
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    place_id VARCHAR(255),
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) DEFAULT '',
                    address TEXT DEFAULT '',
                    website TEXT DEFAULT '',
                    rating REAL DEFAULT 0.0,
                    reviews INTEGER DEFAULT 0,
                    category VARCHAR(255) DEFAULT '',
                    city VARCHAR(255) DEFAULT '',
                    priority VARCHAR(50) DEFAULT 'LOW',
                    whatsapp_number VARCHAR(50) DEFAULT '',
                    source VARCHAR(100) DEFAULT 'google_maps',
                    contacted BOOLEAN DEFAULT FALSE,
                    contact_date TIMESTAMP DEFAULT NULL,
                    notes TEXT DEFAULT '',
                    instagram VARCHAR(255) DEFAULT '',
                    facebook VARCHAR(255) DEFAULT '',
                    custom_pitch TEXT DEFAULT '',
                    is_broken_website BOOLEAN DEFAULT FALSE,
                    line_type VARCHAR(100) DEFAULT '',
                    pipeline_stage VARCHAR(100) DEFAULT 'NEW',
                    email VARCHAR(255) DEFAULT '',
                    remind_date DATE DEFAULT NULL,
                    remind_status VARCHAR(100) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT leads_place_id_user_id_key UNIQUE (place_id, user_id)
                )
            """)

            # Search history table
            run_query("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    query TEXT NOT NULL,
                    city VARCHAR(255) NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    leads_count INTEGER DEFAULT 0,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # WhatsApp message log
            run_query("""
                CREATE TABLE IF NOT EXISTS message_log (
                    id SERIAL PRIMARY KEY,
                    lead_id INTEGER,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    template_used VARCHAR(255) DEFAULT '',
                    message_sent TEXT DEFAULT '',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
                )
            """)

            # Safe migration: add columns and update constraints for existing tables
            run_query("ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id INTEGER;")
            run_query("ALTER TABLE leads ADD COLUMN IF NOT EXISTS audit_data TEXT DEFAULT '';")
            run_query("ALTER TABLE search_history ADD COLUMN IF NOT EXISTS user_id INTEGER;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS user_id INTEGER;")
            
            # Category 3: Outreach & Tracking columns
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS opened BOOLEAN DEFAULT FALSE;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS opened_at TIMESTAMP DEFAULT NULL;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS open_count INTEGER DEFAULT 0;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS clicked BOOLEAN DEFAULT FALSE;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMP DEFAULT NULL;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS click_count INTEGER DEFAULT 0;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS clicked_links TEXT DEFAULT '';")
            
            # Add search metadata columns to search_history table (BUG-M10)
            run_query("ALTER TABLE search_history ADD COLUMN IF NOT EXISTS deep_scan BOOLEAN DEFAULT FALSE;")
            run_query("ALTER TABLE search_history ADD COLUMN IF NOT EXISTS zones TEXT DEFAULT '';")
            run_query("ALTER TABLE search_history ADD COLUMN IF NOT EXISTS include_with_website BOOLEAN DEFAULT FALSE;")
            run_query("ALTER TABLE search_history ADD COLUMN IF NOT EXISTS hide_saved BOOLEAN DEFAULT FALSE;")
            
            # Clean up orphan records before adding constraint to prevent ForeignKeyViolation
            run_query("DELETE FROM leads WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);")
            run_query("DELETE FROM search_history WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);")
            run_query("DELETE FROM message_log WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);")

            run_query("""
                DO $$
                BEGIN
                    -- For leads
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conrelid = 'leads'::regclass AND contype = 'f' 
                        AND (conname = 'fk_leads_users' OR pg_get_constraintdef(oid) ILIKE '%references users(id)%')
                    ) THEN
                        ALTER TABLE leads ADD CONSTRAINT fk_leads_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
                    END IF;
                    
                    -- For search_history
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conrelid = 'search_history'::regclass AND contype = 'f' 
                        AND (conname = 'fk_search_history_users' OR pg_get_constraintdef(oid) ILIKE '%references users(id)%')
                    ) THEN
                        ALTER TABLE search_history ADD CONSTRAINT fk_search_history_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
                    END IF;

                    -- For message_log
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conrelid = 'message_log'::regclass AND contype = 'f' 
                        AND (conname = 'fk_message_log_users' OR pg_get_constraintdef(oid) ILIKE '%references users(id)%')
                    ) THEN
                        ALTER TABLE message_log ADD CONSTRAINT fk_message_log_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
                    END IF;
                END
                $$;
            """)

            # Map existing orphan records to the first user
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1;")
                first_user = cursor.fetchone()
                if first_user:
                    first_user_id = first_user[0]
                    cursor.execute("UPDATE leads SET user_id = %s WHERE user_id IS NULL;", (first_user_id,))
                    cursor.execute("UPDATE search_history SET user_id = %s WHERE user_id IS NULL;", (first_user_id,))
                    cursor.execute("UPDATE message_log SET user_id = %s WHERE user_id IS NULL;", (first_user_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()

            # Drop old single place_id constraint and add composite unique constraint
            run_query("ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_place_id_key;")
            run_query("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'leads_place_id_user_id_key') THEN
                        ALTER TABLE leads ADD CONSTRAINT leads_place_id_user_id_key UNIQUE (place_id, user_id);
                    END IF;
                END
                $$;
            """)

            # ---- PHASE 3: Database Type Migrations ----
            type_migrations = [
                # contacted: INTEGER → BOOLEAN
                "ALTER TABLE leads ALTER COLUMN contacted DROP DEFAULT;",
                "ALTER TABLE leads ALTER COLUMN contacted TYPE BOOLEAN USING contacted::boolean;",
                "ALTER TABLE leads ALTER COLUMN contacted SET DEFAULT FALSE;",
                # is_broken_website: INTEGER → BOOLEAN
                "ALTER TABLE leads ALTER COLUMN is_broken_website DROP DEFAULT;",
                "ALTER TABLE leads ALTER COLUMN is_broken_website TYPE BOOLEAN USING is_broken_website::boolean;",
                "ALTER TABLE leads ALTER COLUMN is_broken_website SET DEFAULT FALSE;",
                # remind_date: VARCHAR → DATE (nullable)
                "ALTER TABLE leads ALTER COLUMN remind_date DROP DEFAULT;",
                "ALTER TABLE leads ALTER COLUMN remind_date TYPE DATE USING NULLIF(remind_date, '')::date;",
                "ALTER TABLE leads ALTER COLUMN remind_date SET DEFAULT NULL;",
                # contact_date: VARCHAR → TIMESTAMP (nullable)
                "ALTER TABLE leads ALTER COLUMN contact_date DROP DEFAULT;",
                "ALTER TABLE leads ALTER COLUMN contact_date TYPE TIMESTAMP USING NULLIF(contact_date, '')::timestamp;",
                "ALTER TABLE leads ALTER COLUMN contact_date SET DEFAULT NULL;",
            ]
            for query in type_migrations:
                run_query(query)

            # ---- PHASE 3: Database Indexes ----
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);",
                "CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);",
                "CREATE INDEX IF NOT EXISTS idx_leads_pipeline ON leads(pipeline_stage);",
                "CREATE INDEX IF NOT EXISTS idx_leads_contacted ON leads(contacted);",
                "CREATE INDEX IF NOT EXISTS idx_leads_remind ON leads(remind_status, remind_date);",
                "CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_search_user_id ON search_history(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_search_date ON search_history(searched_at);",
                "CREATE INDEX IF NOT EXISTS idx_msglog_lead ON message_log(lead_id);",
                "CREATE INDEX IF NOT EXISTS idx_msglog_user ON message_log(user_id);",
            ]
            for query in index_queries:
                run_query(query)

            # Create password_resets table and index for OTP storage
            run_query("""
                CREATE TABLE IF NOT EXISTS password_resets (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    otp VARCHAR(6) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            run_query("CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email);")

            # Create system_settings table
            run_query("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # Reply and Drip tracking columns migration
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS is_reply BOOLEAN DEFAULT FALSE;")
            run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS reply_body TEXT DEFAULT '';")
            
            run_query("ALTER TABLE leads ADD COLUMN IF NOT EXISTS drip_sequence_active BOOLEAN DEFAULT TRUE;")
            run_query("ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_followup_date TIMESTAMP DEFAULT NULL;")
            run_query("ALTER TABLE leads ADD COLUMN IF NOT EXISTS followup_count INTEGER DEFAULT 0;")

            # IMAP settings table
            run_query("""
                CREATE TABLE IF NOT EXISTS imap_settings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    imap_host VARCHAR(255) NOT NULL,
                    imap_port INTEGER DEFAULT 993,
                    imap_email VARCHAR(255) NOT NULL,
                    imap_password_encrypted TEXT NOT NULL,
                    use_ssl BOOLEAN DEFAULT TRUE,
                    last_synced_at TIMESTAMP DEFAULT NULL,
                    CONSTRAINT imap_settings_user_id_key UNIQUE (user_id)
                );
            """)

            # SMTP settings table (persisted for background drips)
            run_query("""
                CREATE TABLE IF NOT EXISTS smtp_settings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    smtp_host VARCHAR(255) NOT NULL,
                    smtp_port INTEGER DEFAULT 465,
                    smtp_email VARCHAR(255) NOT NULL,
                    smtp_password_encrypted TEXT NOT NULL,
                    use_ssl BOOLEAN DEFAULT TRUE,
                    CONSTRAINT smtp_settings_user_id_key UNIQUE (user_id)
                );
            """)

            # Drip configuration settings table
            run_query("""
                CREATE TABLE IF NOT EXISTS drip_configurations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    delay_days INTEGER DEFAULT 3,
                    max_followups INTEGER DEFAULT 2,
                    followup_subject VARCHAR(255) DEFAULT 'Quick follow up regarding proposal',
                    followup_template TEXT DEFAULT '',
                    is_enabled BOOLEAN DEFAULT FALSE,
                    CONSTRAINT drip_configs_user_id_key UNIQUE (user_id)
                );
            """)

            # Extra indexes
            run_query("CREATE INDEX IF NOT EXISTS idx_msglog_is_reply ON message_log(is_reply);")
            run_query("CREATE INDEX IF NOT EXISTS idx_leads_drip ON leads(drip_sequence_active, pipeline_stage);")
        finally:
            self._release_connection(conn)

    def is_user_admin(self, user_id: int) -> bool:
        """Check if a user has admin privileges."""
        if not user_id:
            return False
        try:
            user_id = int(user_id)
        except (ValueError, TypeError) as type_err:
            logging.error(f"[Database] Invalid user_id format passed to is_user_admin: {user_id}. Error: {type_err}")
            return False

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return bool(row and row.get('is_admin'))
        except Exception as e:
            logging.error(f"[Database] Error checking admin privileges for user_id {user_id}: {e}", exc_info=True)
            return False
        finally:
            self._release_connection(conn)

    def save_leads(self, leads: List[Lead], user_id: int) -> int:
        """
        Save leads to the database, updating existing ones for the specific user.
        
        Returns the number of genuinely NEW leads saved (not updates).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        new_count = 0

        try:
            # Pre-fetch existing place_ids for this user to distinguish INSERT from UPDATE
            existing_place_ids = set()
            try:
                cursor.execute("SELECT place_id FROM leads WHERE user_id = %s AND place_id IS NOT NULL AND place_id != ''", (user_id,))
                existing_place_ids = {row[0] for row in cursor.fetchall()}
            except Exception:
                pass

            for lead in leads:
                try:
                    is_new = lead.place_id and lead.place_id not in existing_place_ids
                    cursor.execute("SAVEPOINT save_lead_sp;")
                    # ON CONFLICT update logic matches Postgres syntax with composite key
                    cursor.execute("""
                        INSERT INTO leads (place_id, user_id, name, phone, address, website, rating, 
                                          reviews, category, city, priority, whatsapp_number, source,
                                          is_broken_website, line_type, email)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(place_id, user_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            phone = EXCLUDED.phone,
                            address = EXCLUDED.address,
                            website = EXCLUDED.website,
                            rating = EXCLUDED.rating,
                            reviews = EXCLUDED.reviews,
                            category = EXCLUDED.category,
                            city = EXCLUDED.city,
                            priority = EXCLUDED.priority,
                            whatsapp_number = EXCLUDED.whatsapp_number,
                            is_broken_website = EXCLUDED.is_broken_website,
                            line_type = EXCLUDED.line_type,
                            email = EXCLUDED.email,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        lead.place_id, user_id, lead.name, lead.phone, lead.address,
                        lead.website, lead.rating, lead.reviews, lead.category,
                        lead.city, lead.priority, lead.whatsapp_number, lead.source,
                        lead.is_broken_website, lead.line_type, lead.email
                    ))
                    cursor.execute("RELEASE SAVEPOINT save_lead_sp;")
                    
                    if is_new:
                        new_count += 1
                        existing_place_ids.add(lead.place_id)
                except Exception as e:
                    try:
                        cursor.execute("ROLLBACK TO SAVEPOINT save_lead_sp;")
                    except Exception:
                        pass
                    logging.error(f"Error saving lead {lead.name}: {e}", exc_info=True)
                    continue

            conn.commit()
        except Exception as e:
            logging.error(f"Error in save_leads batch: {e}", exc_info=True)
            conn.rollback()
        finally:
            self._release_connection(conn)
        return new_count

    def save_search(self, query: str, city: str, results_count: int, leads_count: int, user_id: int,
                    deep_scan: bool = False, zones: list = None, include_with_website: bool = False, hide_saved: bool = False):
        """Log a search to the history for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            zones_str = ",".join(zones) if zones else ""
            cursor.execute("""
                INSERT INTO search_history (user_id, query, city, results_count, leads_count, deep_scan, zones, include_with_website, hide_saved)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, query, city, results_count, leads_count, deep_scan, zones_str, include_with_website, hide_saved))
            conn.commit()
        except Exception as e:
            logging.error(f"Error saving search history: {e}", exc_info=True)
            conn.rollback()
        finally:
            self._release_connection(conn)

    def get_all_leads(self, priority_filter: str = None, city_filter: str = None, user_id: int = None) -> List[Dict]:
        """
        Get all leads from the database with optional filters for a specific user.
        When user_id is provided, only returns that user's leads.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM leads WHERE priority != 'IGNORE'"
        params = []
        
        # BUG-L4 fix: Always enforce user_id filter when provided
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)

        if priority_filter:
            query += " AND priority = %s"
            params.append(priority_filter)
        
        if city_filter:
            query += " AND LOWER(city) LIKE %s"
            params.append(f"%{city_filter.lower()}%")

        query += " ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END"

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._release_connection(conn)

    def get_all_leads_paginated(self, priority_filter: str = None, city_filter: str = None, user_id: int = None, page: int = 1, per_page: int = 50) -> Dict:
        """
        Get paginated leads from the database with optional filters for a specific user.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        where_clauses = ["priority != 'IGNORE'"]
        params = []
        
        if user_id is not None:
            where_clauses.append("user_id = %s")
            params.append(user_id)

        if priority_filter:
            where_clauses.append("priority = %s")
            params.append(priority_filter)
        
        if city_filter:
            where_clauses.append("LOWER(city) LIKE %s")
            params.append(f"%{city_filter.lower()}%")

        where_str = " AND ".join(where_clauses)
        
        # Get total count first
        count_query = f"SELECT COUNT(*) FROM leads WHERE {where_str}"
        
        # Paginated query
        offset = (page - 1) * per_page
        query = f"SELECT * FROM leads WHERE {where_str} ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END LIMIT %s OFFSET %s"
        
        try:
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Execute with limit/offset params
            query_params = params + [per_page, offset]
            cursor.execute(query, query_params)
            rows = cursor.fetchall()
            leads = [dict(row) for row in rows]
            
            return {
                "leads": leads,
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "pages": (total_count + per_page - 1) // per_page if total_count > 0 else 1
            }
        finally:
            self._release_connection(conn)

    def get_search_history(self, limit: int = 20, user_id: int = None) -> List[Dict]:
        """Get recent search history for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM search_history"
            params = []
            
            if user_id is not None:
                query += " WHERE user_id = %s"
                params.append(user_id)
                
            query += " ORDER BY searched_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self._release_connection(conn)

    def mark_contacted(self, lead_id: int, notes: str = "", user_id: int = None):
        """Mark a lead as contacted for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                UPDATE leads 
                SET contacted = TRUE, 
                    contact_date = %s, 
                    notes = %s,
                    pipeline_stage = CASE WHEN pipeline_stage = 'NEW' THEN 'PITCHED' ELSE pipeline_stage END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = [datetime.now(), notes, lead_id]
            
            # BUG-L4 fix: Always enforce user_id filter when provided
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
        finally:
            self._release_connection(conn)

    def log_message(self, lead_id: int, template: str, message: str, user_id: int) -> int:
        """Log a WhatsApp or Email message sent to a lead and return its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO message_log (lead_id, user_id, template_used, message_sent)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (lead_id, user_id, template, message))
            log_id = cursor.fetchone()[0]
            conn.commit()
            return log_id
        except Exception as e:
            logging.error(f"[Database] Error logging message: {e}")
            conn.rollback()
            return 0
        finally:
            self._release_connection(conn)

    def get_stats(self, user_id: int = None) -> Dict:
        """Get dashboard statistics for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            stats = {}
            
            # Build query filtering helpers
            where_clause = " WHERE priority != 'IGNORE'"
            params = []
            if user_id is not None:
                where_clause += " AND user_id = %s"
                params.append(user_id)
                
            # Total leads
            cursor.execute("SELECT COUNT(*) FROM leads" + where_clause, params)
            stats["total_leads"] = cursor.fetchone()[0]

            # By priority
            cursor.execute("SELECT COUNT(*) FROM leads" + where_clause + " AND priority = 'HIGH'", params)
            stats["high_priority"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM leads" + where_clause + " AND priority = 'MEDIUM'", params)
            stats["medium_priority"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM leads" + where_clause + " AND priority = 'LOW'", params)
            stats["low_priority"] = cursor.fetchone()[0]

            # Contacted
            cursor.execute("SELECT COUNT(*) FROM leads" + where_clause + " AND contacted = TRUE", params)
            stats["contacted"] = cursor.fetchone()[0]

            # Total searches
            search_where = ""
            search_params = []
            if user_id is not None:
                search_where = " WHERE user_id = %s"
                search_params.append(user_id)
            cursor.execute("SELECT COUNT(*) FROM search_history" + search_where, search_params)
            stats["total_searches"] = cursor.fetchone()[0]

            # Cities covered
            cursor.execute("SELECT COUNT(DISTINCT city) FROM leads" + where_clause, params)
            stats["cities_covered"] = cursor.fetchone()[0]

            # Broken websites
            cursor.execute("SELECT COUNT(*) FROM leads" + where_clause + " AND is_broken_website = TRUE", params)
            stats["broken_websites"] = cursor.fetchone()[0]

            return stats
        finally:
            self._release_connection(conn)

    def delete_lead(self, lead_id: int, user_id: int = None):
        """Delete a lead by ID for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if user_id is not None:
                cursor.execute("DELETE FROM leads WHERE id = %s AND user_id = %s", (lead_id, user_id))
            else:
                cursor.execute("DELETE FROM leads WHERE id = %s", (lead_id,))
            conn.commit()
        finally:
            self._release_connection(conn)

    def cleanup_old_data(self, user_id: int = None):
        """
        Automatically cleans up old data:
        - Keeps all contacted leads
        - Deletes uncontacted leads older than 14 days
        - Deletes IGNORE priority leads older than 7 days
        - Deletes search history older than 30 days
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # PostgreSQL date calculations using parameterized make_interval for safety
            leads_query1 = """
                DELETE FROM leads 
                WHERE contacted = FALSE 
                AND pipeline_stage = 'NEW'
                AND (remind_status IS NULL OR remind_status = '' OR remind_status = 'DISMISSED')
                AND created_at < CURRENT_TIMESTAMP - make_interval(days => %s)
            """
            leads_query2 = """
                DELETE FROM leads 
                WHERE priority = 'IGNORE' 
                AND (remind_status IS NULL OR remind_status = '' OR remind_status = 'DISMISSED')
                AND created_at < CURRENT_TIMESTAMP - make_interval(days => %s)
            """
            history_query = """
                DELETE FROM search_history 
                WHERE searched_at < CURRENT_TIMESTAMP - make_interval(days => %s)
            """
            
            params1 = [CLEANUP_UNCONTACTED_DAYS]
            params2 = [CLEANUP_IGNORED_DAYS]
            params3 = [CLEANUP_HISTORY_DAYS]
            
            if user_id is not None:
                leads_query1 += " AND user_id = %s"
                params1.append(user_id)
                leads_query2 += " AND user_id = %s"
                params2.append(user_id)
                history_query += " AND user_id = %s"
                params3.append(user_id)
            else:
                logging.warning("[Smart Cleanup] Running system-wide cleanup (no user_id scope).")
                
            cursor.execute(leads_query1, params1)
            uncontacted_deleted = cursor.rowcount

            cursor.execute(leads_query2, params2)
            ignored_deleted = cursor.rowcount

            cursor.execute(history_query, params3)
            history_deleted = cursor.rowcount

            conn.commit()
            if uncontacted_deleted or ignored_deleted or history_deleted:
                logging.info(f"[Smart Cleanup] Auto-cleaned old database entries:")
                logging.info(f"  - Deleted {uncontacted_deleted} uncontacted leads (>14 days)")
                logging.info(f"  - Deleted {ignored_deleted} ignored website leads (>7 days)")
                logging.info(f"  - Deleted {history_deleted} old search history entries (>30 days)")
        except Exception as e:
            logging.error(f"[Smart Cleanup] Error cleaning up old data: {e}")
        finally:
            self._release_connection(conn)

    def clear_uncontacted_data(self, user_id: int = None) -> dict:
        """
        Manually clears all uncontacted leads and ignored leads, keeping only contacted ones.
        Also clears all search history for a user.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            leads_clause = " WHERE contacted = FALSE"
            history_clause = ""
            params = []
            
            if user_id is not None:
                leads_clause += " AND user_id = %s"
                history_clause = " WHERE user_id = %s"
                params = [user_id]
                
            cursor.execute("SELECT COUNT(*) FROM leads" + leads_clause, params)
            uncontacted_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM search_history" + history_clause, params)
            history_count = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM leads" + leads_clause, params)
            cursor.execute("DELETE FROM search_history" + history_clause, params)
            
            conn.commit()
            return {
                "success": True,
                "leads_deleted": uncontacted_count,
                "history_deleted": history_count
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self._release_connection(conn)

    def update_lead_socials(self, lead_id: int, instagram: str, facebook: str, user_id: int = None) -> bool:
        """Update Instagram and Facebook links for a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                UPDATE leads
                SET instagram = %s,
                    facebook = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = [instagram, facebook, lead_id]
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating socials for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_lead_by_id(self, lead_id: int, user_id: int = None) -> Optional[Dict]:
        """Fetch a single lead by its database ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if user_id is not None:
                cursor.execute("SELECT * FROM leads WHERE id = %s AND user_id = %s", (lead_id, user_id))
            else:
                cursor.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"Error fetching lead by ID {lead_id}: {e}")
            return None
        finally:
            self._release_connection(conn)

    def update_lead_pitch(self, lead_id: int, custom_pitch: str, user_id: int = None) -> bool:
        """Update the custom AI generated pitch for a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                UPDATE leads
                SET custom_pitch = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = [custom_pitch, lead_id]
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating custom pitch for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def update_lead_pipeline_stage(self, lead_id: int, stage: str, user_id: int = None) -> bool:
        """Update the pipeline stage of a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if stage == "PITCHED":
                query = """
                    UPDATE leads
                    SET pipeline_stage = %s,
                        contacted = TRUE,
                        contact_date = CASE WHEN contact_date IS NULL THEN %s ELSE contact_date END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                params = [stage, datetime.now(), lead_id]
            else:
                query = """
                    UPDATE leads
                    SET pipeline_stage = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                params = [stage, lead_id]
                
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating pipeline stage for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def update_lead_email(self, lead_id: int, email: str, user_id: int = None) -> bool:
        """Update the scraped email address for a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                UPDATE leads
                SET email = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = [email, lead_id]
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating email for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def schedule_reminder(self, lead_id: int, remind_date: str, user_id: int = None) -> bool:
        """Schedule a follow-up reminder date for a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                UPDATE leads
                SET remind_date = %s,
                    remind_status = 'PENDING',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = [remind_date, lead_id]
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error scheduling reminder for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_pending_reminders(self, user_id: int = None) -> List[Dict]:
        """Fetch all leads that have a pending follow-up reminder."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT * FROM leads 
                WHERE remind_date IS NOT NULL 
                AND remind_status = 'PENDING'
            """
            params = []
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
            query += " ORDER BY remind_date ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Error fetching pending reminders: {e}")
            return []
        finally:
            self._release_connection(conn)

    def dismiss_reminder(self, lead_id: int, user_id: int = None) -> bool:
        """Dismiss/complete a follow-up reminder for a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                UPDATE leads
                SET remind_status = 'DISMISSED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            params = [lead_id]
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error dismissing reminder for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def create_user(self, username, email, password_hash, phone="") -> bool:
        """Create a new user with hashed password, email, and contact number."""
        normalized_username = username.strip()
        normalized_email = email.strip().lower()
        normalized_phone = phone.strip()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, phone)
                VALUES (%s, %s, %s, %s)
            """, (normalized_username, normalized_email, password_hash, normalized_phone))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error creating user {normalized_username} ({normalized_email}): {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_user_by_email(self, email) -> Optional[Dict]:
        """Fetch a user by email (case-insensitive)."""
        normalized_email = email.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (normalized_email,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"Error fetching user by email {normalized_email}: {e}")
            return None
        finally:
            self._release_connection(conn)

    def get_user_by_username(self, username) -> Optional[Dict]:
        """Fetch a user by username (case-insensitive)."""
        normalized_username = username.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = %s", (normalized_username,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"Error fetching user by username {normalized_username}: {e}")
            return None
        finally:
            self._release_connection(conn)

    def toggle_user_active(self, user_id: int, status: bool) -> bool:
        """Toggle a user's is_active status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (status, user_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error toggling active status for user {user_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def toggle_user_admin(self, user_id: int, status: bool) -> bool:
        """Toggle a user's is_admin status."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_admin = %s WHERE id = %s", (status, user_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error toggling admin status for user {user_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def delete_user_account(self, user_id: int) -> bool:
        """Delete a user account. Deletes all associated records via cascade."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def save_password_reset_otp(self, email, otp, expires_at) -> bool:
        """Save or update an OTP code for password resets."""
        normalized_email = email.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Delete old resets for the email first, and also clean up all expired OTP records
            cursor.execute("DELETE FROM password_resets WHERE email = %s", (normalized_email,))
            cursor.execute("DELETE FROM password_resets WHERE expires_at < CURRENT_TIMESTAMP")
            cursor.execute("""
                INSERT INTO password_resets (email, otp, expires_at)
                VALUES (%s, %s, %s)
            """, (normalized_email, otp, expires_at))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error saving password reset OTP for {normalized_email}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def verify_password_reset_otp(self, email, otp) -> bool:
        """Verify if the OTP is correct and hasn't expired."""
        normalized_email = email.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 1 FROM password_resets
                WHERE email = %s AND otp = %s AND expires_at > CURRENT_TIMESTAMP
            """, (normalized_email, otp))
            row = cursor.fetchone()
            return bool(row)
        except Exception as e:
            logging.error(f"Error verifying password reset OTP for {normalized_email}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def delete_password_reset_otp(self, email) -> bool:
        """Clear the password reset entries for an email."""
        normalized_email = email.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM password_resets WHERE email = %s", (normalized_email,))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error deleting password reset records for {normalized_email}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def update_user_password(self, email, password_hash) -> bool:
        """Update a user's password hash in the users table."""
        normalized_email = email.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET password_hash = %s
                WHERE LOWER(email) = %s
            """, (password_hash, normalized_email))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating password for {normalized_email}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_system_setting(self, key: str, default: str = "") -> str:
        """Retrieve a system setting value by key."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM system_settings WHERE key = %s", (key,))
            row = cursor.fetchone()
            return row[0] if row else default
        except Exception as e:
            logging.error(f"[Database] Error retrieving system setting '{key}': {e}")
            return default
        finally:
            self._release_connection(conn)

    def save_system_setting(self, key: str, value: str) -> bool:
        """Save or update a system setting value by key."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO system_settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving system setting '{key}': {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

    def update_lead_audit_data(self, lead_id: int, audit_data_str: str, user_id: int = None) -> bool:
        """Update the audit_data JSON string for a specific lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "UPDATE leads SET audit_data = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            params = [audit_data_str, lead_id]
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error updating audit data for lead {lead_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

    def get_lead_outreach_logs(self, lead_id: int, user_id: int) -> List[Dict]:
        """Retrieve message logs with tracking parameters for a specific lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, template_used, message_sent, sent_at, opened, opened_at, open_count, clicked, clicked_at, click_count, clicked_links, is_reply, reply_body
                FROM message_log
                WHERE lead_id = %s AND user_id = %s
                ORDER BY sent_at DESC;
            """, (lead_id, user_id))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"[Database] Error retrieving outreach logs for lead {lead_id}: {e}")
            return []
        finally:
            self._release_connection(conn)

    def record_email_open(self, log_id: int) -> bool:
        """Record an email open event for the given log ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE message_log
                SET opened = TRUE,
                    opened_at = CURRENT_TIMESTAMP,
                    open_count = open_count + 1
                WHERE id = %s
            """, (log_id,))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error recording email open for log {log_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

    def record_link_click(self, log_id: int, dest_url: str) -> int:
        """Record a link click event and return the associated lead_id (or 0)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # First, update the message log
            cursor.execute("""
                UPDATE message_log
                SET clicked = TRUE,
                    clicked_at = CURRENT_TIMESTAMP,
                    click_count = click_count + 1,
                    clicked_links = CASE 
                        WHEN clicked_links IS NULL OR clicked_links = '' THEN %s 
                        ELSE clicked_links || ', ' || %s 
                    END
                WHERE id = %s
                RETURNING lead_id;
            """, (dest_url, dest_url, log_id))
            row = cursor.fetchone()
            lead_id = row[0] if row else 0
            conn.commit()
            return lead_id
        except Exception as e:
            logging.error(f"[Database] Error recording link click for log {log_id}: {e}")
            conn.rollback()
            return 0
        finally:
            self._release_connection(conn)

    # ---- Encryption Helpers ----
    def _encrypt_password(self, password: str) -> str:
        if not password:
            return ""
        try:
            from config import Config
            key_source = Config.SECRET_KEY or "fallback_secret_key_1234567890_!"
            import hashlib, base64
            key = hashlib.sha256(key_source.encode('utf-8')).digest()
            encrypted = bytes(a ^ b for a, b in zip(password.encode('utf-8'), key * (len(password) // len(key) + 1)))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logging.error(f"[Database] Error encrypting credential password: {e}")
            return password

    def _decrypt_password(self, encrypted_password: str) -> str:
        if not encrypted_password:
            return ""
        try:
            from config import Config
            key_source = Config.SECRET_KEY or "fallback_secret_key_1234567890_!"
            import hashlib, base64
            key = hashlib.sha256(key_source.encode('utf-8')).digest()
            encrypted = base64.b64decode(encrypted_password.encode('utf-8'))
            decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
            return decrypted.decode('utf-8')
        except Exception as e:
            logging.error(f"[Database] Error decrypting credential password: {e}")
            return encrypted_password

    # ---- Inbound Reply Helper ----
    def record_inbound_reply(self, lead_id: int, user_id: int, sender_email: str, reply_text: str) -> bool:
        """Log incoming email reply and advance pipeline stage to REPLIED."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 1. Insert inbound reply into message_log
            cursor.execute("""
                INSERT INTO message_log (lead_id, user_id, template_used, message_sent, is_reply, reply_body)
                VALUES (%s, %s, 'email_reply', %s, TRUE, %s)
            """, (lead_id, user_id, reply_text, reply_text))
            
            # 2. Update lead's pipeline stage and last contact status
            cursor.execute("""
                UPDATE leads
                SET pipeline_stage = 'REPLIED',
                    contacted = TRUE,
                    contact_date = CURRENT_TIMESTAMP,
                    drip_sequence_active = FALSE
                WHERE id = %s AND user_id = %s
            """, (lead_id, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error recording inbound reply for lead {lead_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

    # ---- IMAP Settings Accessors ----
    def get_imap_settings(self, user_id: int) -> Optional[Dict]:
        """Fetch and decrypt IMAP mail configurations for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT imap_host, imap_port, imap_email, imap_password_encrypted, use_ssl, last_synced_at
                FROM imap_settings WHERE user_id = %s
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["password"] = self._decrypt_password(res.pop("imap_password_encrypted"))
            res["host"] = res.pop("imap_host")
            res["port"] = res.pop("imap_port")
            res["email"] = res.pop("imap_email")
            return res
        except Exception as e:
            logging.error(f"[Database] Error getting IMAP settings for user {user_id}: {e}")
            return None
        finally:
            self._release_connection(conn)

    def save_imap_settings(self, user_id: int, host: str, port: int, email: str, password_raw: str, use_ssl: bool) -> bool:
        """Encrypt and save IMAP mail configurations for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        encrypted_pass = self._encrypt_password(password_raw)
        try:
            cursor.execute("""
                INSERT INTO imap_settings (user_id, imap_host, imap_port, imap_email, imap_password_encrypted, use_ssl)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET imap_host = EXCLUDED.imap_host,
                    imap_port = EXCLUDED.imap_port,
                    imap_email = EXCLUDED.imap_email,
                    imap_password_encrypted = EXCLUDED.imap_password_encrypted,
                    use_ssl = EXCLUDED.use_ssl
            """, (user_id, host, port, email, encrypted_pass, use_ssl))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving IMAP settings for user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

    # ---- SMTP Settings Accessors ----
    def get_smtp_settings(self, user_id: int) -> Optional[Dict]:
        """Fetch and decrypt SMTP configurations for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT smtp_host, smtp_port, smtp_email, smtp_password_encrypted, use_ssl
                FROM smtp_settings WHERE user_id = %s
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["password"] = self._decrypt_password(res.pop("smtp_password_encrypted"))
            res["host"] = res.pop("smtp_host")
            res["port"] = res.pop("smtp_port")
            res["email"] = res.pop("smtp_email")
            return res
        except Exception as e:
            logging.error(f"[Database] Error getting SMTP settings for user {user_id}: {e}")
            return None
        finally:
            self._release_connection(conn)

    def save_smtp_settings(self, user_id: int, host: str, port: int, email: str, password_raw: str, use_ssl: bool) -> bool:
        """Encrypt and save SMTP configurations for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        encrypted_pass = self._encrypt_password(password_raw)
        try:
            cursor.execute("""
                INSERT INTO smtp_settings (user_id, smtp_host, smtp_port, smtp_email, smtp_password_encrypted, use_ssl)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET smtp_host = EXCLUDED.smtp_host,
                    smtp_port = EXCLUDED.smtp_port,
                    smtp_email = EXCLUDED.smtp_email,
                    smtp_password_encrypted = EXCLUDED.smtp_password_encrypted,
                    use_ssl = EXCLUDED.use_ssl
            """, (user_id, host, port, email, encrypted_pass, use_ssl))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving SMTP settings for user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

    # ---- Drip Configurations Accessors ----
    def get_drip_config(self, user_id: int) -> Optional[Dict]:
        """Fetch Drip Configuration settings for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT delay_days, max_followups, followup_subject, followup_template, is_enabled
                FROM drip_configurations WHERE user_id = %s
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)
        except Exception as e:
            logging.error(f"[Database] Error getting Drip configuration for user {user_id}: {e}")
            return None
        finally:
            self._release_connection(conn)

    def save_drip_config(self, user_id: int, delay_days: int, max_followups: int, followup_subject: str, followup_template: str, is_enabled: bool) -> bool:
        """Save Drip Configuration settings for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO drip_configurations (user_id, delay_days, max_followups, followup_subject, followup_template, is_enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET delay_days = EXCLUDED.delay_days,
                    max_followups = EXCLUDED.max_followups,
                    followup_subject = EXCLUDED.followup_subject,
                    followup_template = EXCLUDED.followup_template,
                    is_enabled = EXCLUDED.is_enabled
            """, (user_id, delay_days, max_followups, followup_subject, followup_template, is_enabled))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving Drip configuration for user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._release_connection(conn)

