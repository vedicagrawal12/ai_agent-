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


class Database:
    """PostgreSQL database manager for lead storage."""

    # Class-level connection pool
    _pool = None
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
            print("[Database] WARNING: DATABASE_URL contains placeholder password. Falling back to default 'postgres' password.")
            db_url = db_url.replace("YOUR_POSTGRES_PASSWORD", "postgres")
        self.db_url = db_url

        # Initialize thread-safe connection pool once
        with Database._pool_lock:
            if Database._pool is None:
                logging.info("[Database] Initializing connection pool...")
                Database._pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    dsn=self.db_url,
                    cursor_factory=psycopg2.extras.DictCursor
                )

        self._init_db()
        # Run startup cleanup once, outside of _init_db
        # BUG-M8 fix: Use lock to prevent race condition in multi-worker environments
        with Database._cleanup_lock:
            if not Database._cleanup_done:
                Database._cleanup_done = True
                self.cleanup_old_data()

    def _get_connection(self):
        """Get a database connection from the connection pool."""
        return Database._pool.getconn()

    def _release_connection(self, conn):
        """Release a database connection back to the pool."""
        if conn:
            Database._pool.putconn(conn)

    def _init_db(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()

        def run_query(query, params=None):
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logging.debug(f"[Database Init] Query skipped/failed: {query}. Error: {e}")

        # Users table (created if not exists, with password_hash as TEXT and email column)
        run_query("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) DEFAULT '',
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Safe migration: ensure existing password_hash column is TYPE TEXT, email, is_admin, and is_active columns exist
        run_query("ALTER TABLE users ALTER COLUMN password_hash TYPE TEXT;")
        run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) DEFAULT '';")
        run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
        run_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        run_query("UPDATE users SET is_admin = TRUE WHERE id = (SELECT MIN(id) FROM users) AND is_admin = FALSE;")

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
        run_query("ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
        run_query("ALTER TABLE search_history ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
        run_query("ALTER TABLE message_log ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;")
        
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

        self._release_connection(conn)

    def is_user_admin(self, user_id: int) -> bool:
        """Check if a user has admin privileges."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return bool(row and row.get('is_admin'))
        except Exception:
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
                    
                    if is_new:
                        new_count += 1
                        existing_place_ids.add(lead.place_id)
                except Exception as e:
                    print(f"Error saving lead {lead.name}: {e}")
                    continue

            conn.commit()
        except Exception as e:
            print(f"Error in save_leads batch: {e}")
            conn.rollback()
        finally:
            self._release_connection(conn)
        return new_count

    def save_search(self, query: str, city: str, results_count: int, leads_count: int, user_id: int):
        """Log a search to the history for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO search_history (user_id, query, city, results_count, leads_count)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, query, city, results_count, leads_count))
            conn.commit()
        except Exception as e:
            print(f"Error saving search history: {e}")
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
            
            if user_id:
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
            params = [datetime.now().isoformat(), notes, lead_id]
            
            # BUG-L4 fix: Always enforce user_id filter when provided
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cursor.execute(query, params)
            conn.commit()
        finally:
            self._release_connection(conn)

    def log_message(self, lead_id: int, template: str, message: str, user_id: int):
        """Log a WhatsApp message sent to a lead for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO message_log (lead_id, user_id, template_used, message_sent)
                VALUES (%s, %s, %s, %s)
            """, (lead_id, user_id, template, message))
            conn.commit()
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
            if user_id:
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
            if user_id:
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

    def cleanup_old_data(self):
        """
        Automatically cleans up old data on startup:
        - Keeps all contacted leads
        - Deletes uncontacted leads older than 14 days
        - Deletes IGNORE priority leads older than 7 days
        - Deletes search history older than 30 days
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # PostgreSQL date calculations: CURRENT_TIMESTAMP - INTERVAL 'X days'
            cursor.execute("""
                DELETE FROM leads 
                WHERE contacted = FALSE 
                AND pipeline_stage = 'NEW'
                AND (remind_status IS NULL OR remind_status = '' OR remind_status = 'DISMISSED')
                AND created_at < CURRENT_TIMESTAMP - INTERVAL '14 days'
            """)
            uncontacted_deleted = cursor.rowcount

            cursor.execute("""
                DELETE FROM leads 
                WHERE priority = 'IGNORE' 
                AND (remind_status IS NULL OR remind_status = '' OR remind_status = 'DISMISSED')
                AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
            """)
            ignored_deleted = cursor.rowcount

            cursor.execute("""
                DELETE FROM search_history 
                WHERE searched_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
            """)
            history_deleted = cursor.rowcount

            conn.commit()
            if uncontacted_deleted or ignored_deleted or history_deleted:
                print(f"[Smart Cleanup] Auto-cleaned old database entries:")
                print(f"  - Deleted {uncontacted_deleted} uncontacted leads (>14 days)")
                print(f"  - Deleted {ignored_deleted} ignored website leads (>7 days)")
                print(f"  - Deleted {history_deleted} old search history entries (>30 days)")
        except Exception as e:
            print(f"[Smart Cleanup] Error cleaning up old data: {e}")
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
            
            if user_id:
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
            print(f"Error updating socials for lead {lead_id}: {e}")
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
            print(f"Error fetching lead by ID {lead_id}: {e}")
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
            print(f"Error updating custom pitch for lead {lead_id}: {e}")
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
                params = [stage, datetime.now().isoformat(), lead_id]
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
            print(f"Error updating pipeline stage for lead {lead_id}: {e}")
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
            print(f"Error updating email for lead {lead_id}: {e}")
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
            print(f"Error scheduling reminder for lead {lead_id}: {e}")
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
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            query += " ORDER BY remind_date ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching pending reminders: {e}")
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
            print(f"Error dismissing reminder for lead {lead_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def create_user(self, username, email, password_hash) -> bool:
        """Create a new user with hashed password and email."""
        normalized_username = username.strip().lower()
        normalized_email = email.strip()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
            """, (normalized_username, normalized_email, password_hash))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating user {normalized_username}: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_user_by_username(self, username) -> Optional[Dict]:
        """Fetch a user by username (case-insensitive)."""
        normalized_username = username.strip().lower()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (normalized_username,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching user by username {normalized_username}: {e}")
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
            print(f"Error toggling active status for user {user_id}: {e}")
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
            print(f"Error toggling admin status for user {user_id}: {e}")
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
            print(f"Error deleting user {user_id}: {e}")
            return False
        finally:
            self._release_connection(conn)

