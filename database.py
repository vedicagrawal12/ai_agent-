"""
Database Manager — SQLite storage for leads and search history.

Stores collected leads persistently so you can:
- Track which leads you've already contacted
- View past search results
- Export historical data
- Avoid re-collecting the same leads
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict
from collectors.base_collector import Lead


class Database:
    """SQLite database manager for lead storage."""

    def __init__(self, db_path: str = "leads.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Leads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id TEXT UNIQUE,
                name TEXT NOT NULL,
                phone TEXT DEFAULT '',
                address TEXT DEFAULT '',
                website TEXT DEFAULT '',
                rating REAL DEFAULT 0.0,
                reviews INTEGER DEFAULT 0,
                category TEXT DEFAULT '',
                city TEXT DEFAULT '',
                priority TEXT DEFAULT 'LOW',
                whatsapp_number TEXT DEFAULT '',
                source TEXT DEFAULT 'google_maps',
                contacted INTEGER DEFAULT 0,
                contact_date TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                instagram TEXT DEFAULT '',
                facebook TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add columns dynamically for backward compatibility with existing databases
        try:
            cursor.execute("PRAGMA table_info(leads)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'instagram' not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN instagram TEXT DEFAULT ''")
            if 'facebook' not in columns:
                cursor.execute("ALTER TABLE leads ADD COLUMN facebook TEXT DEFAULT ''")
        except Exception as alter_err:
            print(f"Error altering table for social columns: {alter_err}")

        # Search history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                city TEXT NOT NULL,
                results_count INTEGER DEFAULT 0,
                leads_count INTEGER DEFAULT 0,
                searched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # WhatsApp message log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                template_used TEXT DEFAULT '',
                message_sent TEXT DEFAULT '',
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        """)

        conn.commit()
        conn.close()
        self.cleanup_old_data()

    def save_leads(self, leads: List[Lead]) -> int:
        """
        Save leads to the database, updating existing ones.
        
        Returns the number of new leads saved.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        new_count = 0

        for lead in leads:
            try:
                cursor.execute("""
                    INSERT INTO leads (place_id, name, phone, address, website, rating, 
                                      reviews, category, city, priority, whatsapp_number, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(place_id) DO UPDATE SET
                        name = excluded.name,
                        phone = excluded.phone,
                        address = excluded.address,
                        website = excluded.website,
                        rating = excluded.rating,
                        reviews = excluded.reviews,
                        category = excluded.category,
                        city = excluded.city,
                        priority = excluded.priority,
                        whatsapp_number = excluded.whatsapp_number,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    lead.place_id, lead.name, lead.phone, lead.address,
                    lead.website, lead.rating, lead.reviews, lead.category,
                    lead.city, lead.priority, lead.whatsapp_number, lead.source
                ))
                
                if cursor.rowcount > 0:
                    new_count += 1
            except Exception as e:
                print(f"Error saving lead {lead.name}: {e}")
                continue

        conn.commit()
        conn.close()
        return new_count

    def save_search(self, query: str, city: str, results_count: int, leads_count: int):
        """Log a search to the history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_history (query, city, results_count, leads_count)
            VALUES (?, ?, ?, ?)
        """, (query, city, results_count, leads_count))
        conn.commit()
        conn.close()

    def get_all_leads(self, priority_filter: str = None, city_filter: str = None) -> List[Dict]:
        """
        Get all leads from the database with optional filters.
        
        Args:
            priority_filter: Filter by priority (HIGH, MEDIUM, LOW)
            city_filter: Filter by city name
            
        Returns:
            List of lead dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM leads WHERE priority != 'IGNORE'"
        params = []

        if priority_filter:
            query += " AND priority = ?"
            params.append(priority_filter)
        
        if city_filter:
            query += " AND LOWER(city) LIKE ?"
            params.append(f"%{city_filter.lower()}%")

        query += " ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_search_history(self, limit: int = 20) -> List[Dict]:
        """Get recent search history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM search_history 
            ORDER BY searched_at DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_contacted(self, lead_id: int, notes: str = ""):
        """Mark a lead as contacted."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads 
            SET contacted = 1, 
                contact_date = ?, 
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (datetime.now().isoformat(), notes, lead_id))
        conn.commit()
        conn.close()

    def log_message(self, lead_id: int, template: str, message: str):
        """Log a WhatsApp message sent to a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO message_log (lead_id, template_used, message_sent)
            VALUES (?, ?, ?)
        """, (lead_id, template, message))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get dashboard statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}
        
        # Total leads
        cursor.execute("SELECT COUNT(*) FROM leads WHERE priority != 'IGNORE'")
        stats["total_leads"] = cursor.fetchone()[0]

        # By priority
        cursor.execute("SELECT COUNT(*) FROM leads WHERE priority = 'HIGH'")
        stats["high_priority"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads WHERE priority = 'MEDIUM'")
        stats["medium_priority"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads WHERE priority = 'LOW'")
        stats["low_priority"] = cursor.fetchone()[0]

        # Contacted
        cursor.execute("SELECT COUNT(*) FROM leads WHERE contacted = 1")
        stats["contacted"] = cursor.fetchone()[0]

        # Total searches
        cursor.execute("SELECT COUNT(*) FROM search_history")
        stats["total_searches"] = cursor.fetchone()[0]

        # Cities covered
        cursor.execute("SELECT COUNT(DISTINCT city) FROM leads WHERE priority != 'IGNORE'")
        stats["cities_covered"] = cursor.fetchone()[0]

        conn.close()
        return stats

    def delete_lead(self, lead_id: int):
        """Delete a lead by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        conn.commit()
        conn.close()

    def cleanup_old_data(self):
        """
        Automatically cleans up old data on startup:
        - Keeps all contacted leads (outreach log protection)
        - Deletes uncontacted leads older than 14 days
        - Deletes IGNORE priority leads (have websites) older than 7 days
        - Deletes search history older than 30 days
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 1. Delete uncontacted leads older than 14 days
            cursor.execute("""
                DELETE FROM leads 
                WHERE contacted = 0 
                AND created_at < datetime('now', '-14 days')
            """)
            uncontacted_deleted = cursor.rowcount

            # 2. Delete IGNORE leads (which have websites) older than 7 days
            cursor.execute("""
                DELETE FROM leads 
                WHERE priority = 'IGNORE' 
                AND created_at < datetime('now', '-7 days')
            """)
            ignored_deleted = cursor.rowcount

            # 3. Delete search history older than 30 days
            cursor.execute("""
                DELETE FROM search_history 
                WHERE searched_at < datetime('now', '-30 days')
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
            conn.close()

    def clear_uncontacted_data(self) -> dict:
        """
        Manually clears all uncontacted leads and ignored leads, keeping only contacted ones.
        Also clears all search history.
        
        Returns:
            Dict with success flag and count of deleted rows.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Get counts first for reporting
            cursor.execute("SELECT COUNT(*) FROM leads WHERE contacted = 0")
            uncontacted_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM search_history")
            history_count = cursor.fetchone()[0]
            
            # Delete uncontacted leads
            cursor.execute("DELETE FROM leads WHERE contacted = 0")
            
            # Delete search history
            cursor.execute("DELETE FROM search_history")
            
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
            conn.close()

    def update_lead_socials(self, lead_id: int, instagram: str, facebook: str) -> bool:
        """Update Instagram and Facebook links for a lead."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE leads
                SET instagram = ?,
                    facebook = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (instagram, facebook, lead_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating socials for lead {lead_id}: {e}")
            return False
        finally:
            conn.close()

    def get_lead_by_id(self, lead_id: int) -> Optional[Dict]:
        """Fetch a single lead by its database ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching lead by ID {lead_id}: {e}")
            return None
        finally:
            conn.close()
