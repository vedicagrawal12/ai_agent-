import psycopg2
import psycopg2.extras
import json
import os
import logging
import threading
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional, Dict

# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, func, case
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, scoped_session

from collectors.base_collector import Lead
from constants import CLEANUP_UNCONTACTED_DAYS, CLEANUP_IGNORED_DAYS, CLEANUP_HISTORY_DAYS
from models import (
    Base, UserModel, LeadModel, SearchHistoryModel, MessageLogModel,
    PasswordResetsModel, SystemSettingsModel, ImapSettingsModel,
    SmtpSettingsModel, DripConfigurationsModel
)

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def to_dict(row):
    if not row:
        return {}
    res = {}
    for column in row.__table__.columns:
        res[column.name] = getattr(row, column.name)
    return res

class Database:
    """PostgreSQL database manager using SQLAlchemy ORM for lead storage."""

    # Class-level engine and scoped sessions
    _engine = None
    _session_factory = None
    _scoped_session = None
    _pool_lock = threading.Lock()
    _pool_dsn = None

    # Class-level flag to prevent double cleanup
    _cleanup_done = False
    _cleanup_lock = threading.Lock()

    def __init__(self, db_url: str = None):
        """Initialize database connection and create tables if needed."""
        if not db_url:
            db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/leadhunter_db")
        # Handle case where DATABASE_URL still has the placeholder
        if "YOUR_POSTGRES_PASSWORD" in db_url:
            logging.warning("[Database] DATABASE_URL contains placeholder password. Falling back to default 'postgres' password.")
            db_url = db_url.replace("YOUR_POSTGRES_PASSWORD", "postgres")
        # Handle postgres:// vs postgresql:// scheme for psycopg2 compatibility on Render
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self.db_url = db_url
        # Log the connection URL (mask password for security)
        try:
            from urllib.parse import urlparse
            _parsed = urlparse(self.db_url)
            logging.info(f"[Database] Final db_url: scheme={_parsed.scheme} host={_parsed.hostname} port={_parsed.port} db={_parsed.path} user={_parsed.username}")
        except Exception:
            logging.info(f"[Database] Final db_url (raw, first 30 chars): {self.db_url[:30]}...")

        # Initialize engine and scoped session pool once
        with Database._pool_lock:
            # If the database URL has changed, dispose of the old engine
            if Database._engine is not None and Database._pool_dsn != self.db_url:
                logging.info("[Database] Database URL changed. Disposing old engine...")
                try:
                    Database._engine.dispose()
                except Exception as close_err:
                    logging.error(f"[Database] Error disposing engine: {close_err}")
                Database._engine = None

            if Database._engine is None:
                logging.info(f"[Database] Initializing SQLAlchemy engine with URL: {self.db_url}...")
                
                if self.db_url.startswith("sqlite"):
                    Database._engine = create_engine(
                        self.db_url,
                        connect_args={"check_same_thread": False},
                        pool_pre_ping=True
                    )
                else:
                    # Custom creator to ensure raw psycopg2 connections default to DictCursor for compatibility
                    def get_psycopg2_connection():
                        from urllib.parse import urlparse, unquote
                        url = urlparse(self.db_url)
                        conn_kwargs = {
                            "cursor_factory": psycopg2.extras.DictCursor
                        }
                        if url.username:
                            conn_kwargs["user"] = unquote(url.username)
                        if url.password:
                            conn_kwargs["password"] = unquote(url.password)
                        if url.hostname:
                            conn_kwargs["host"] = url.hostname
                        if url.port:
                            conn_kwargs["port"] = url.port
                        else:
                            # Default PostgreSQL port when not specified (common on Render)
                            conn_kwargs["port"] = 5432
                        if url.path and len(url.path) > 1:
                            # Strip leading slash from path to get dbname
                            db_name = url.path.lstrip('/')
                            if db_name:
                                conn_kwargs["database"] = db_name
                        # Log exactly what we're connecting with (mask password)
                        safe_kwargs = {k: ('***' if k == 'password' else v) for k, v in conn_kwargs.items() if k != 'cursor_factory'}
                        logging.info(f"[Database] psycopg2.connect kwargs: {safe_kwargs}")
                        return psycopg2.connect(**conn_kwargs)
    
                    Database._engine = create_engine(
                        "postgresql://",
                        creator=get_psycopg2_connection,
                        pool_size=10,
                        max_overflow=20,
                        pool_pre_ping=True
                    )
                Database._session_factory = sessionmaker(bind=Database._engine)
                Database._scoped_session = scoped_session(Database._session_factory)
                Database._pool_dsn = self.db_url

        self._init_db()

    @property
    def session(self):
        """Return the current thread-local scoped session."""
        return Database._scoped_session()

    def remove_session(self):
        """Dispose of the current scoped session."""
        with Database._pool_lock:
            if Database._scoped_session is not None:
                Database._scoped_session.remove()

    def _get_connection(self):
        """Get a raw psycopg2 connection from the SQLAlchemy engine (for backward compatibility)."""
        return Database._engine.raw_connection()

    def _release_connection(self, conn):
        """Release/close the raw connection."""
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    def close(self):
        """Dispose of the database engine."""
        with Database._pool_lock:
            if Database._engine is not None:
                try:
                    Database._engine.dispose()
                except Exception:
                    pass
                Database._engine = None
                Database._scoped_session = None
                Database._session_factory = None
                Database._pool_dsn = None

    def _init_db(self):
        """Create database tables using SQLAlchemy ORM models."""
        try:
            Base.metadata.create_all(Database._engine)
            
            # Add dynamic tracking columns to existing leads table if they don't exist
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute("ALTER TABLE leads ADD COLUMN whatsapp_sent BOOLEAN DEFAULT FALSE;")
                    conn.commit()
                except Exception:
                    conn.rollback()
                
                try:
                    cursor.execute("ALTER TABLE leads ADD COLUMN social_task_status VARCHAR(50) DEFAULT 'NONE';")
                    conn.commit()
                except Exception:
                    conn.rollback()
                
                try:
                    cursor.execute("ALTER TABLE leads ADD COLUMN social_task_completed_at TIMESTAMP;")
                    conn.commit()
                except Exception:
                    conn.rollback()
            finally:
                self._release_connection(conn)

            # Ensure at least one admin exists (equivalent to old seed query)
            session = self.session
            has_admin = session.query(UserModel).filter_by(is_admin=True).first()
            if not has_admin:
                first_user = session.query(UserModel).order_by(UserModel.id.asc()).first()
                if first_user:
                    first_user.is_admin = True
                    session.commit()
                else:
                    session.rollback()
            else:
                session.rollback()
        except Exception as e:
            logging.error(f"[Database Init] Failed to run schema creation: {e}", exc_info=True)
            try:
                self.session.rollback()
            except Exception:
                pass
        finally:
            self.remove_session()

    def is_user_admin(self, user_id: int) -> bool:
        """Check if a user has admin privileges."""
        if not user_id:
            return False
        try:
            user_id = int(user_id)
        except (ValueError, TypeError) as type_err:
            logging.error(f"[Database] Invalid user_id format passed to is_user_admin: {user_id}. Error: {type_err}")
            return False

        session = self.session
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            return bool(user and user.is_admin)
        except Exception as e:
            logging.error(f"[Database] Error checking admin privileges for user_id {user_id}: {e}", exc_info=True)
            return False

    def is_user_active(self, user_id: int) -> bool:
        """Check if a user account is active."""
        if not user_id:
            return False
        try:
            user_id = int(user_id)
        except (ValueError, TypeError) as type_err:
            logging.error(f"[Database] Invalid user_id format passed to is_user_active: {user_id}. Error: {type_err}")
            return False

        session = self.session
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            return bool(user and user.is_active)
        except Exception as e:
            logging.error(f"[Database] Error checking active status for user_id {user_id}: {e}", exc_info=True)
            return False

    def save_leads(self, leads: List[Lead], user_id: int) -> int:
        """
        Save leads to the database, updating existing ones for the specific user.
        Returns the number of genuinely NEW leads saved.
        """
        session = self.session
        new_count = 0

        try:
            # Pre-fetch existing place_ids for this user to distinguish INSERT from UPDATE
            existing = session.query(LeadModel.place_id).filter(
                LeadModel.user_id == user_id, 
                LeadModel.place_id != None, 
                LeadModel.place_id != ''
            ).all()
            existing_place_ids = {r[0] for r in existing}

            for lead in leads:
                try:
                    is_new = lead.place_id and lead.place_id not in existing_place_ids
                    
                    with session.begin_nested():
                        db_lead = None
                        if lead.place_id:
                            db_lead = session.query(LeadModel).filter_by(place_id=lead.place_id, user_id=user_id).first()
                        
                        if not db_lead:
                            db_lead = LeadModel(place_id=lead.place_id, user_id=user_id)
                            session.add(db_lead)

                        db_lead.name = lead.name
                        db_lead.phone = lead.phone or ''
                        db_lead.address = lead.address or ''
                        db_lead.website = lead.website or ''
                        db_lead.rating = lead.rating or 0.0
                        db_lead.reviews = lead.reviews or 0
                        db_lead.category = lead.category or ''
                        db_lead.city = lead.city or ''
                        db_lead.priority = lead.priority or 'LOW'
                        db_lead.whatsapp_number = lead.whatsapp_number or ''
                        db_lead.source = lead.source or 'google_maps'
                        db_lead.is_broken_website = bool(lead.is_broken_website)
                        db_lead.line_type = lead.line_type or ''
                        db_lead.email = lead.email or ''
                        db_lead.updated_at = utcnow()
                        
                        session.flush()

                    if is_new:
                        new_count += 1
                        existing_place_ids.add(lead.place_id)
                except Exception as e:
                    logging.error(f"Error saving lead {getattr(lead, 'name', 'Unknown')}: {e}")
                    continue

            session.commit()
        except Exception as e:
            logging.error(f"Error in save_leads batch: {e}", exc_info=True)
            session.rollback()
        return new_count

    def save_search(self, query: str, city: str, results_count: int, leads_count: int, user_id: int,
                    deep_scan: bool = False, zones: list = None, include_with_website: bool = False, hide_saved: bool = False):
        """Log a search to the history for a specific user."""
        session = self.session
        try:
            zones_str = ",".join(zones) if zones else ""
            sh = SearchHistoryModel(
                user_id=user_id,
                query=query,
                city=city,
                results_count=results_count,
                leads_count=leads_count,
                deep_scan=deep_scan,
                zones=zones_str,
                include_with_website=include_with_website,
                hide_saved=hide_saved
            )
            session.add(sh)
            session.commit()
        except Exception as e:
            logging.error(f"Error saving search history: {e}", exc_info=True)
            session.rollback()

    def get_all_leads(self, priority_filter: str = None, city_filter: str = None, user_id: int = None) -> List[Dict]:
        """Get all leads from the database with optional filters for a specific user."""
        if user_id is None:
            return []
        session = self.session
        try:
            query = session.query(LeadModel).filter(LeadModel.priority != 'IGNORE')
            query = query.filter_by(user_id=user_id)
            if priority_filter:
                query = query.filter_by(priority=priority_filter)
            if city_filter:
                query = query.filter(LeadModel.city.ilike(f"%{city_filter}%"))

            priority_order = case(
                (LeadModel.priority == 'HIGH', 1),
                (LeadModel.priority == 'MEDIUM', 2),
                (LeadModel.priority == 'LOW', 3),
                else_=4
            )
            rows = query.order_by(priority_order).all()
            return [to_dict(r) for r in rows]
        except Exception as e:
            logging.error(f"Error getting all leads: {e}", exc_info=True)
            return []

    def get_all_leads_paginated(self, priority_filter: str = None, city_filter: str = None, user_id: int = None, page: int = 1, per_page: int = 50) -> Dict:
        """Get paginated leads from the database with optional filters for a specific user."""
        if user_id is None:
            return {
                "leads": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "pages": 1
            }
        session = self.session
        try:
            query = session.query(LeadModel).filter(LeadModel.priority != 'IGNORE')
            query = query.filter_by(user_id=user_id)
            if priority_filter:
                query = query.filter_by(priority=priority_filter)
            if city_filter:
                query = query.filter(LeadModel.city.ilike(f"%{city_filter}%"))

            total_count = query.count()
            offset = (page - 1) * per_page

            priority_order = case(
                (LeadModel.priority == 'HIGH', 1),
                (LeadModel.priority == 'MEDIUM', 2),
                (LeadModel.priority == 'LOW', 3),
                else_=4
            )
            rows = query.order_by(priority_order).limit(per_page).offset(offset).all()
            leads = [to_dict(r) for r in rows]

            return {
                "leads": leads,
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "pages": (total_count + per_page - 1) // per_page if total_count > 0 else 1
            }
        except Exception as e:
            logging.error(f"Error getting leads paginated: {e}", exc_info=True)
            return {
                "leads": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "pages": 1
            }

    def get_search_history(self, limit: int = 20, user_id: int = None) -> List[Dict]:
        """Get recent search history for a specific user."""
        if user_id is None:
            return []
        session = self.session
        try:
            query = session.query(SearchHistoryModel)
            query = query.filter_by(user_id=user_id)
            rows = query.order_by(SearchHistoryModel.searched_at.desc()).limit(limit).all()
            return [to_dict(r) for r in rows]
        except Exception as e:
            logging.error(f"Error getting search history: {e}", exc_info=True)
            return []

    def mark_contacted(self, lead_id: int, notes: str = "", user_id: int = None):
        """Mark a lead as contacted for a specific user."""
        if user_id is None:
            return
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.contacted = True
                lead.contact_date = utcnow()
                lead.notes = notes
                if lead.pipeline_stage == 'NEW':
                    lead.pipeline_stage = 'PITCHED'
                lead.updated_at = utcnow()
                session.commit()
        except Exception as e:
            logging.error(f"Error marking lead contacted: {e}", exc_info=True)
            session.rollback()

    def log_message(self, lead_id: int, template: str, message: str, user_id: int) -> int:
        """Log a WhatsApp or Email message sent to a lead and return its ID."""
        session = self.session
        try:
            log = MessageLogModel(
                lead_id=lead_id,
                user_id=user_id,
                template_used=template,
                message_sent=message
            )
            session.add(log)
            session.commit()
            return log.id
        except Exception as e:
            logging.error(f"[Database] Error logging message: {e}", exc_info=True)
            session.rollback()
            return 0

    def complete_social_task(self, lead_id: int, user_id: int) -> bool:
        """Mark a Day 5 social connection/DM task as completed."""
        session = self.session
        try:
            lead = session.query(LeadModel).filter_by(id=lead_id, user_id=user_id).first()
            if lead:
                lead.social_task_status = 'COMPLETED'
                lead.social_task_completed_at = utcnow()
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"[Database] Error completing social task for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def update_whatsapp_sent(self, lead_id: int, sent: bool, user_id: int) -> bool:
        """Update the whatsapp_sent tracking status for a lead."""
        session = self.session
        try:
            lead = session.query(LeadModel).filter_by(id=lead_id, user_id=user_id).first()
            if lead:
                lead.whatsapp_sent = sent
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"[Database] Error updating WhatsApp status for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def update_whatsapp_reply_received(self, lead_id: int, replied: bool) -> bool:
        """Update the whatsapp_reply_received tracking status for a lead."""
        session = self.session
        try:
            lead = session.query(LeadModel).filter_by(id=lead_id).first()
            if lead:
                lead.whatsapp_reply_received = replied
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"[Database] Error updating WhatsApp reply status for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_omnichannel_leads(self, user_id: int) -> List[Dict]:
        """Fetch all leads enrolled in outreach sequence with email/WhatsApp/social status."""
        session = self.session
        try:
            leads = (session.query(LeadModel)
                     .filter_by(user_id=user_id)
                     .filter(LeadModel.priority != 'IGNORE')
                     .order_by(LeadModel.created_at.desc())
                     .all())
            res = []
            for l in leads:
                d = to_dict(l)
                logs = (session.query(MessageLogModel)
                        .filter_by(lead_id=l.id, user_id=user_id)
                        .order_by(MessageLogModel.sent_at.desc())
                        .all())
                
                email_sent = False
                email_opened = False
                email_clicked = False
                email_replied = False
                
                for log in logs:
                    if log.template_used in ("cold_email", "drip_followup_1", "drip_followup_2"):
                        email_sent = True
                        if log.opened:
                            email_opened = True
                        if log.clicked:
                            email_clicked = True
                        if log.is_reply:
                            email_replied = True
                
                d["email_sent"] = email_sent
                d["email_opened"] = email_opened
                d["email_clicked"] = email_clicked
                d["email_replied"] = email_replied
                
                whatsapp_replied = False
                for log in logs:
                    if log.template_used in ("website_pitch", "digital_presence", "simple_intro", "custom"):
                        if log.is_reply:
                            whatsapp_replied = True
                            
                d["whatsapp_replied"] = whatsapp_replied
                res.append(d)
            return res
        except Exception as e:
            logging.error(f"[Database] Error fetching omnichannel leads: {e}", exc_info=True)
            return []

    def get_omnichannel_campaign_stats(self, user_id: int) -> Dict:
        """Fetch aggregated campaign stats for omnichannel outreach sequence."""
        session = self.session
        try:
            leads = (session.query(LeadModel)
                     .filter_by(user_id=user_id)
                     .filter(LeadModel.priority != 'IGNORE')
                     .all())
            
            total_leads = len(leads)
            emails_sent = 0
            emails_opened = 0
            emails_clicked = 0
            emails_replied = 0
            whatsapps_sent = sum(1 for l in leads if l.whatsapp_sent)
            whatsapps_pending = 0
            social_tasks_pending = sum(1 for l in leads if l.social_task_status == 'PENDING')
            social_tasks_completed = sum(1 for l in leads if l.social_task_status == 'COMPLETED')
            
            for l in leads:
                has_email = False
                has_open = False
                has_click = False
                has_reply = False
                
                logs = (session.query(MessageLogModel)
                        .filter_by(lead_id=l.id, user_id=user_id)
                        .all())
                
                for log in logs:
                    if log.template_used in ("cold_email", "drip_followup_1", "drip_followup_2"):
                        has_email = True
                        if log.opened:
                            has_open = True
                        if log.clicked:
                            has_click = True
                        if log.is_reply:
                            has_reply = True
                
                if has_email:
                    emails_sent += 1
                if has_open:
                    emails_opened += 1
                if has_click:
                    emails_clicked += 1
                if has_reply:
                    emails_replied += 1
                
                if has_email and not l.whatsapp_sent and l.pipeline_stage in ('PITCHED', 'NEW') and not has_reply:
                    whatsapps_pending += 1
            
            return {
                "total_leads": total_leads,
                "emails_sent": emails_sent,
                "emails_opened": emails_opened,
                "emails_clicked": emails_clicked,
                "emails_replied": emails_replied,
                "whatsapps_sent": whatsapps_sent,
                "whatsapps_pending": whatsapps_pending,
                "social_tasks_pending": social_tasks_pending,
                "social_tasks_completed": social_tasks_completed
            }
        except Exception as e:
            logging.error(f"[Database] Error fetching omnichannel stats: {e}", exc_info=True)
            return {
                "total_leads": 0, "emails_sent": 0, "emails_opened": 0, "emails_clicked": 0, "emails_replied": 0,
                "whatsapps_sent": 0, "whatsapps_pending": 0, "social_tasks_pending": 0, "social_tasks_completed": 0
            }

    def get_stats(self, user_id: int = None) -> Dict:
        """Get dashboard statistics for a specific user."""
        if user_id is None:
            return {
                "total_leads": 0, "high_priority": 0, "medium_priority": 0, "low_priority": 0,
                "contacted": 0, "total_searches": 0, "cities_covered": 0, "broken_websites": 0
            }
        session = self.session
        try:
            query = session.query(LeadModel).filter(LeadModel.priority != 'IGNORE')
            query = query.filter_by(user_id=user_id)

            total_leads = query.count()
            high_priority = query.filter_by(priority='HIGH').count()
            medium_priority = query.filter_by(priority='MEDIUM').count()
            low_priority = query.filter_by(priority='LOW').count()
            contacted = query.filter_by(contacted=True).count()
            broken_websites = query.filter_by(is_broken_website=True).count()

            # Cities covered
            cities_covered = query.with_entities(func.count(func.distinct(LeadModel.city))).scalar() or 0

            # Total searches
            sh_query = session.query(SearchHistoryModel)
            sh_query = sh_query.filter_by(user_id=user_id)
            total_searches = sh_query.count()

            return {
                "total_leads": total_leads,
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority,
                "contacted": contacted,
                "total_searches": total_searches,
                "cities_covered": cities_covered,
                "broken_websites": broken_websites
            }
        except Exception as e:
            logging.error(f"Error getting database stats: {e}", exc_info=True)
            return {}

    def delete_lead(self, lead_id: int, user_id: int = None):
        """Delete a lead by ID for a specific user."""
        if user_id is None:
            return
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                session.delete(lead)
                session.commit()
        except Exception as e:
            logging.error(f"Error deleting lead: {e}", exc_info=True)
            session.rollback()

    def get_recent_delivered_emails(self, user_id: int, hours: int = 12) -> List[Dict]:
        """Fetch email messages sent within the specified hour limit for a user."""
        session = self.session
        try:
            from datetime import timedelta
            cutoff = utcnow() - timedelta(hours=hours)
            
            rows = (session.query(MessageLogModel)
                    .join(LeadModel, MessageLogModel.lead_id == LeadModel.id)
                    .filter(MessageLogModel.user_id == user_id)
                    .filter(MessageLogModel.sent_at >= cutoff)
                    .filter(MessageLogModel.template_used.like('cold_email%') | MessageLogModel.template_used.like('drip_followup_%'))
                    .order_by(MessageLogModel.sent_at.desc())
                    .all())
            
            res = []
            for r in rows:
                d = to_dict(r)
                d["lead_name"] = r.lead.name if r.lead else "Unknown"
                d["lead_email"] = r.lead.email if r.lead else ""
                res.append(d)
            return res
        except Exception as e:
            logging.error(f"[Database] Error fetching recent delivered emails: {e}", exc_info=True)
            return []

    def cleanup_old_data(self, user_id: int = None):
        """Automatically cleans up old data based on retention constants."""
        session = self.session
        try:
            from datetime import timedelta
            cutoff_uncontacted = utcnow() - timedelta(days=CLEANUP_UNCONTACTED_DAYS)
            cutoff_ignored = utcnow() - timedelta(days=CLEANUP_IGNORED_DAYS)
            cutoff_history = utcnow() - timedelta(days=CLEANUP_HISTORY_DAYS)
            cutoff_logs = utcnow() - timedelta(days=30)

            query1 = session.query(LeadModel).filter(
                LeadModel.contacted == False,
                LeadModel.pipeline_stage == 'NEW',
                (LeadModel.remind_status == None) | (LeadModel.remind_status == '') | (LeadModel.remind_status == 'DISMISSED'),
                LeadModel.created_at < cutoff_uncontacted
            )

            query2 = session.query(LeadModel).filter(
                LeadModel.priority == 'IGNORE',
                (LeadModel.remind_status == None) | (LeadModel.remind_status == '') | (LeadModel.remind_status == 'DISMISSED'),
                LeadModel.created_at < cutoff_ignored
            )

            query3 = session.query(SearchHistoryModel).filter(
                SearchHistoryModel.searched_at < cutoff_history
            )

            query4 = session.query(MessageLogModel).filter(
                MessageLogModel.sent_at < cutoff_logs
            )

            if user_id is not None:
                query1 = query1.filter_by(user_id=user_id)
                query2 = query2.filter_by(user_id=user_id)
                query3 = query3.filter_by(user_id=user_id)
                query4 = query4.filter_by(user_id=user_id)
            else:
                logger.warning("[Smart Cleanup] Running system-wide cleanup (no user_id scope).")

            uncontacted_deleted = query1.delete(synchronize_session=False)
            ignored_deleted = query2.delete(synchronize_session=False)
            history_deleted = query3.delete(synchronize_session=False)
            logs_deleted = query4.delete(synchronize_session=False)

            session.commit()
            if uncontacted_deleted or ignored_deleted or history_deleted or logs_deleted:
                logging.info(f"[Smart Cleanup] Auto-cleaned old database entries:")
                logging.info(f"  - Deleted {uncontacted_deleted} uncontacted leads")
                logging.info(f"  - Deleted {ignored_deleted} ignored website leads")
                logging.info(f"  - Deleted {history_deleted} old search history entries")
                logging.info(f"  - Deleted {logs_deleted} old message logs (older than 30 days)")
        except Exception as e:
            logging.error(f"[Smart Cleanup] Error cleaning up old data: {e}", exc_info=True)
            session.rollback()

    def clear_uncontacted_data(self, user_id: int = None) -> dict:
        """Manually clears all uncontacted leads, ignored leads, and search history."""
        if user_id is None:
            return {
                "success": False,
                "error": "User ID is required"
            }
        session = self.session
        try:
            leads_query = session.query(LeadModel).filter(LeadModel.contacted == False)
            history_query = session.query(SearchHistoryModel)

            leads_query = leads_query.filter_by(user_id=user_id)
            history_query = history_query.filter_by(user_id=user_id)

            uncontacted_count = leads_query.count()
            history_count = history_query.count()

            leads_query.delete(synchronize_session=False)
            history_query.delete(synchronize_session=False)

            session.commit()
            return {
                "success": True,
                "leads_deleted": uncontacted_count,
                "history_deleted": history_count
            }
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def update_lead_socials(self, lead_id: int, instagram: str, facebook: str, user_id: int = None) -> bool:
        """Update Instagram and Facebook links for a lead."""
        if user_id is None:
            return False
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.instagram = instagram
                lead.facebook = facebook
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating socials for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_lead_by_id(self, lead_id: int, user_id: int = None) -> Optional[Dict]:
        """Fetch a single lead by its database ID."""
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            lead = query.first()
            return to_dict(lead) if lead else None
        except Exception as e:
            logging.error(f"Error fetching lead by ID {lead_id}: {e}", exc_info=True)
            return None

    def get_competitors_benchmark(self, lead_id: int, user_id: int = None) -> Dict:
        """Fetch/generate competitor comparison metrics matrix for a lead."""
        session = self.session
        try:
            # 1. Get target lead
            lead = session.query(LeadModel).filter_by(id=lead_id).first()
            if not lead:
                return {"lead": {}, "competitors": []}
            
            # Use the provided user_id, or fall back to the lead's owner
            effective_user_id = user_id if user_id is not None else lead.user_id
            
            # Project lead fields directly to avoid returning datetime/metadata objects
            lead_dict = {
                "id": lead.id,
                "name": lead.name,
                "website": lead.website,
                "rating": lead.rating,
                "reviews": lead.reviews,
                "category": lead.category,
                "city": lead.city,
                "phone": lead.phone,
                "whatsapp_number": lead.whatsapp_number,
                "email": lead.email,
                "custom_pitch": lead.custom_pitch,
                "is_broken_website": lead.is_broken_website
            }
            
            # Parse audit data if present
            lead_audit = {}
            if lead.audit_data:
                try:
                    lead_audit = json.loads(lead.audit_data)
                except Exception:
                    pass
            
            # Extract lead's own audit scores
            lead_dict['speed_score'] = lead_audit.get('scores', {}).get('speed', 0) if lead_audit else 0
            lead_dict['seo_score'] = lead_audit.get('scores', {}).get('seo', 0) if lead_audit else 0
            lead_dict['mobile_score'] = lead_audit.get('scores', {}).get('mobile', 0) if lead_audit else 0
            lead_dict['ssl_score'] = lead_audit.get('scores', {}).get('ssl', 0) if lead_audit else 0
            lead_dict['overall_score'] = lead_audit.get('overall_score', 0) if lead_audit else 0
            
            # 2. Get real database competitors
            competitors = []
            if lead.city and lead.category:
                # Same user_id, same city, same category (case-insensitive)
                db_comps = (session.query(LeadModel)
                            .filter(LeadModel.user_id == effective_user_id)
                            .filter(LeadModel.id != lead.id)
                            .filter(func.lower(LeadModel.city) == func.lower(lead.city))
                            .filter(func.lower(LeadModel.category) == func.lower(lead.category))
                            .filter(LeadModel.priority != 'IGNORE')
                            .limit(3)
                            .all())
                
                for c in db_comps:
                    c_audit = {}
                    if c.audit_data:
                        try:
                            c_audit = json.loads(c.audit_data)
                        except Exception:
                            pass
                    
                    # Project competitor fields directly, excluding datetimes
                    c_dict = {
                        "id": c.id,
                        "name": c.name,
                        "website": c.website,
                        "rating": c.rating,
                        "reviews": c.reviews,
                        "category": c.category,
                        "city": c.city,
                        "speed_score": c_audit.get('scores', {}).get('speed', 80) if c_audit else (80 if c.website else 0),
                        "seo_score": c_audit.get('scores', {}).get('seo', 85) if c_audit else (85 if c.website else 0),
                        "mobile_score": c_audit.get('scores', {}).get('mobile', 100) if c_audit else (100 if c.website else 0),
                        "ssl_score": c_audit.get('scores', {}).get('ssl', 100) if c_audit else (100 if c.website else 0),
                        "overall_score": c_audit.get('overall_score', 85) if c_audit else (85 if c.website else 0),
                        "is_mock": False
                    }
                    competitors.append(c_dict)
            
            # 3. Fallback logic: generate mockup competitors if fewer than 2 exist
            if len(competitors) < 2:
                needed = 3 - len(competitors)
                cat_lower = (lead.category or "").lower()
                city_name = lead.city or "Local"
                
                niche_names = []
                if any(k in cat_lower for k in ['gym', 'fitness', 'yoga', 'crossfit', 'workout', 'pilates']):
                    niche_names = ["Pulse Fitness Center", "Iron Strength Gym", "Peak Performance Club"]
                elif any(k in cat_lower for k in ['salon', 'spa', 'barber', 'beauty', 'hair']):
                    niche_names = ["Glow & Style Lounge", "Enchante Beauty Salon", "Urban Salon & Spa"]
                elif any(k in cat_lower for k in ['restaurant', 'cafe', 'hotel', 'bakery', 'food']):
                    niche_names = ["The Daily Grind Cafe", "The Spice Table", f"Bistro {city_name}"]
                elif any(k in cat_lower for k in ['dentist', 'dental', 'clinic', 'doctor', 'health']):
                    niche_names = ["Apex Dental Care", "CareFirst Clinic", "Metro Health Centre"]
                elif any(k in cat_lower for k in ['school', 'coaching', 'tutor', 'academy', 'education']):
                    niche_names = ["Pinnacle Coaching Institute", "Elite Success Academy", "Alpha Tutoring"]
                elif any(k in cat_lower for k in ['real estate', 'builder', 'interior', 'construction']):
                    niche_names = ["Horizon Real Estate", "Prime Realty Group", "Urban Design Studio"]
                else:
                    niche_names = [f"Apex {lead.category or 'Business'} Studio", f"Premier {lead.category or 'Business'} Co.", f"Elite {lead.category or 'Business'} Partners"]
                
                import random
                # Use a local RNG instance seeded with lead_id for stable, repeatable
                # mock competitors — without corrupting the global random state.
                rng = random.Random(lead_id)
                
                for i in range(needed):
                    comp_name = niche_names[i % len(niche_names)]
                    
                    # Avoid duplicate name collision with target lead or other competitors
                    attempt = 0
                    suffixes = [" Elite", " Pro", " Premium", " Choice", " Group"]
                    base_comp_name = comp_name
                    while (
                        (lead.name and comp_name.strip().lower() == lead.name.strip().lower()) or 
                        any(c["name"].strip().lower() == comp_name.strip().lower() for c in competitors)
                    ):
                        suffix = suffixes[attempt % len(suffixes)]
                        comp_name = f"{base_comp_name}{suffix}"
                        attempt += 1
                    
                    lead_reviews = lead.reviews or 0
                    comp_rating = round(rng.uniform(4.3, 4.8), 1)
                    comp_reviews = int(lead_reviews * rng.uniform(1.2, 1.8)) + rng.randint(15, 50)
                    
                    comp_speed = rng.randint(85, 96)
                    comp_seo = rng.randint(85, 95)
                    comp_mobile = 100
                    comp_ssl = 100
                    comp_overall = int((comp_speed * 0.3) + (comp_seo * 0.3) + (comp_mobile * 0.2) + (comp_ssl * 0.1) + (100 * 0.1))
                    
                    competitors.append({
                        "id": -1 - i,
                        "name": comp_name,
                        "website": f"https://{comp_name.lower().replace(' & ', '-').replace(' ', '')}.com",
                        "phone": f"+91 98765 4321{i}",
                        "rating": comp_rating,
                        "reviews": comp_reviews,
                        "category": lead.category,
                        "city": lead.city,
                        "speed_score": comp_speed,
                        "seo_score": comp_seo,
                        "mobile_score": comp_mobile,
                        "ssl_score": comp_ssl,
                        "overall_score": comp_overall,
                        "is_mock": True
                    })
            
            return {
                "lead": lead_dict,
                "competitors": competitors[:3]
            }
        except Exception as e:
            logging.error(f"Error compiling competitors benchmark for lead {lead_id}: {e}", exc_info=True)
            return {"lead": {}, "competitors": []}
        finally:
            self.remove_session()

    def update_lead_pitch(self, lead_id: int, custom_pitch: str, user_id: int = None) -> bool:
        """Update the custom AI generated pitch for a lead."""
        if user_id is None:
            return False
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.custom_pitch = custom_pitch
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating custom pitch for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def update_lead_pipeline_stage(self, lead_id: int, stage: str, user_id: int = None) -> bool:
        """Update the pipeline stage of a lead."""
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.pipeline_stage = stage
                if stage == "PITCHED":
                    lead.contacted = True
                    if lead.contact_date is None:
                        lead.contact_date = utcnow()
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating pipeline stage for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def update_lead_email(self, lead_id: int, email: str, user_id: int = None) -> bool:
        """Update the scraped email address for a lead."""
        if user_id is None:
            return False
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.email = email
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating email for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def schedule_reminder(self, lead_id: int, remind_date: str, user_id: int = None) -> bool:
        """Schedule a follow-up reminder date for a lead."""
        if user_id is None:
            return False
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                if isinstance(remind_date, str):
                    try:
                        dt = datetime.strptime(remind_date, "%Y-%m-%d").date()
                    except Exception:
                        dt = datetime.strptime(remind_date.split("T")[0], "%Y-%m-%d").date()
                else:
                    dt = remind_date
                
                lead.remind_date = dt
                lead.remind_status = 'PENDING'
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error scheduling reminder for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_pending_reminders(self, user_id: int = None) -> List[Dict]:
        """Fetch all leads that have a pending follow-up reminder."""
        if user_id is None:
            return []
        session = self.session
        try:
            query = session.query(LeadModel).filter(
                LeadModel.remind_date != None,
                LeadModel.remind_status == 'PENDING'
            )
            query = query.filter_by(user_id=user_id)
            rows = query.order_by(LeadModel.remind_date.asc()).all()
            return [to_dict(r) for r in rows]
        except Exception as e:
            logging.error(f"Error fetching pending reminders: {e}", exc_info=True)
            return []

    def dismiss_reminder(self, lead_id: int, user_id: int = None) -> bool:
        """Dismiss/complete a follow-up reminder for a lead."""
        if user_id is None:
            return False
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.remind_status = 'DISMISSED'
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error dismissing reminder for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def create_user(self, username, email, password_hash, phone="") -> bool:
        """Create a new user with hashed password, email, and contact number."""
        session = self.session
        try:
            user = UserModel(
                username=username.strip(),
                email=email.strip().lower(),
                password_hash=password_hash,
                phone=phone.strip()
            )
            session.add(user)
            session.commit()
            return True
        except Exception as e:
            logging.error(f"Error creating user {username}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_user_by_email(self, email) -> Optional[Dict]:
        """Fetch a user by email (case-insensitive)."""
        session = self.session
        try:
            user = session.query(UserModel).filter(func.lower(UserModel.email) == email.strip().lower()).first()
            return to_dict(user) if user else None
        except Exception as e:
            logging.error(f"Error fetching user by email {email}: {e}", exc_info=True)
            return None

    def get_user_by_username(self, username) -> Optional[Dict]:
        """Fetch a user by username (case-insensitive)."""
        session = self.session
        try:
            user = session.query(UserModel).filter(func.lower(UserModel.username) == username.strip().lower()).first()
            return to_dict(user) if user else None
        except Exception as e:
            logging.error(f"Error fetching user by username {username}: {e}", exc_info=True)
            return None

    def toggle_user_active(self, user_id: int, status: bool) -> bool:
        """Toggle a user's is_active status."""
        session = self.session
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                user.is_active = status
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error toggling active status for user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def toggle_user_admin(self, user_id: int, status: bool) -> bool:
        """Toggle a user's is_admin status."""
        session = self.session
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                user.is_admin = status
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error toggling admin status for user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def delete_user_account(self, user_id: int) -> bool:
        """Delete a user account. Deletes all associated records via cascade."""
        session = self.session
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def save_password_reset_otp(self, email, otp, expires_at) -> bool:
        """Save or update an OTP code for password resets."""
        normalized_email = email.strip().lower()
        session = self.session
        try:
            # Delete old resets for the email, and clean up expired OTP records
            session.query(PasswordResetsModel).filter_by(email=normalized_email).delete()
            session.query(PasswordResetsModel).filter(PasswordResetsModel.expires_at < datetime.now()).delete()
            
            reset = PasswordResetsModel(
                email=normalized_email,
                otp=otp,
                expires_at=expires_at
            )
            session.add(reset)
            session.commit()
            return True
        except Exception as e:
            logging.error(f"Error saving password reset OTP for {normalized_email}: {e}", exc_info=True)
            session.rollback()
            return False

    def verify_password_reset_otp(self, email, otp) -> bool:
        """Verify if the OTP is correct and hasn't expired."""
        normalized_email = email.strip().lower()
        session = self.session
        try:
            reset = session.query(PasswordResetsModel).filter(
                PasswordResetsModel.email == normalized_email,
                PasswordResetsModel.otp == otp,
                PasswordResetsModel.expires_at > datetime.now()
            ).first()
            return bool(reset)
        except Exception as e:
            logging.error(f"Error verifying password reset OTP for {normalized_email}: {e}", exc_info=True)
            return False

    def delete_password_reset_otp(self, email) -> bool:
        """Clear the password reset entries for an email."""
        normalized_email = email.strip().lower()
        session = self.session
        try:
            session.query(PasswordResetsModel).filter_by(email=normalized_email).delete()
            session.commit()
            return True
        except Exception as e:
            logging.error(f"Error deleting password reset records for {normalized_email}: {e}", exc_info=True)
            session.rollback()
            return False

    def update_user_password(self, email, password_hash) -> bool:
        """Update a user's password hash in the users table."""
        normalized_email = email.strip().lower()
        session = self.session
        try:
            user = session.query(UserModel).filter(func.lower(UserModel.email) == normalized_email).first()
            if user:
                user.password_hash = password_hash
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating password for {normalized_email}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_system_setting(self, key: str, default: str = "") -> str:
        """Retrieve a system setting value by key."""
        session = self.session
        try:
            setting = session.query(SystemSettingsModel).filter_by(key=key).first()
            return setting.value if setting else default
        except Exception as e:
            logging.error(f"[Database] Error retrieving system setting '{key}': {e}", exc_info=True)
            return default

    def save_system_setting(self, key: str, value: str) -> bool:
        """Save or update a system setting value by key."""
        session = self.session
        try:
            setting = session.query(SystemSettingsModel).filter_by(key=key).first()
            if not setting:
                setting = SystemSettingsModel(key=key)
                session.add(setting)
            setting.value = value
            session.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving system setting '{key}': {e}", exc_info=True)
            session.rollback()
            return False

    def update_lead_audit_data(self, lead_id: int, audit_data_str: str, user_id: int = None) -> bool:
        """Update the audit_data JSON string for a specific lead."""
        if user_id is None:
            return False
        session = self.session
        try:
            query = session.query(LeadModel).filter_by(id=lead_id)
            query = query.filter_by(user_id=user_id)
            lead = query.first()
            if lead:
                lead.audit_data = audit_data_str
                lead.updated_at = utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"[Database] Error updating audit data for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_lead_outreach_logs(self, lead_id: int, user_id: int) -> List[Dict]:
        """Retrieve message logs with tracking parameters for a specific lead."""
        session = self.session
        try:
            rows = session.query(MessageLogModel).filter_by(
                lead_id=lead_id, 
                user_id=user_id
            ).order_by(MessageLogModel.sent_at.desc()).all()
            return [to_dict(r) for r in rows]
        except Exception as e:
            logging.error(f"[Database] Error retrieving outreach logs for lead {lead_id}: {e}", exc_info=True)
            return []

    def record_email_open(self, log_id: int) -> bool:
        """Record an email open event for the given log ID."""
        session = self.session
        try:
            log = session.query(MessageLogModel).filter_by(id=log_id).first()
            if log:
                log.opened = True
                log.opened_at = utcnow()
                log.open_count = (log.open_count or 0) + 1
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"[Database] Error recording email open for log {log_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def record_link_click(self, log_id: int, dest_url: str) -> int:
        """Record a link click event and return the associated lead_id (or 0)."""
        session = self.session
        try:
            log = session.query(MessageLogModel).filter_by(id=log_id).first()
            if log:
                log.clicked = True
                log.clicked_at = utcnow()
                log.click_count = (log.click_count or 0) + 1
                if not log.clicked_links:
                    log.clicked_links = dest_url
                else:
                    log.clicked_links += f", {dest_url}"
                lead_id = log.lead_id or 0
                session.commit()
                return lead_id
            return 0
        except Exception as e:
            logging.error(f"[Database] Error recording link click for log {log_id}: {e}", exc_info=True)
            session.rollback()
            return 0

    def update_message_content(self, log_id: int, message: str) -> bool:
        """Update the stored message body/HTML content for a given log ID."""
        session = self.session
        try:
            log = session.query(MessageLogModel).filter_by(id=log_id).first()
            if log:
                log.message_sent = message
                session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"[Database] Error updating message content for log {log_id}: {e}", exc_info=True)
            session.rollback()
            return False

    # ---- Encryption Helpers ----
    def _encrypt_password(self, password: str) -> str:
        if not password:
            return ""
        try:
            from cryptography.fernet import Fernet
            import base64
            import hashlib
            import os

            key_source = os.getenv("FLASK_SECRET_KEY")
            if not key_source:
                key_source = self.get_system_setting("credential_encryption_secret")
                if not key_source:
                    import secrets
                    key_source = secrets.token_hex(32)
                    self.save_system_setting("credential_encryption_secret", key_source)

            key = hashlib.sha256(key_source.encode('utf-8')).digest()
            fernet_key = base64.urlsafe_b64encode(key)
            f = Fernet(fernet_key)
            return f.encrypt(password.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logging.error(f"[Database] Error encrypting credential password: {e}", exc_info=True)
            return password

    def _decrypt_password(self, encrypted_password: str) -> str:
        if not encrypted_password:
            return ""
        # Try Fernet first
        try:
            from cryptography.fernet import Fernet
            import base64
            import hashlib
            import os
            
            key_source = os.getenv("FLASK_SECRET_KEY")
            if not key_source:
                key_source = self.get_system_setting("credential_encryption_secret")
                if not key_source:
                    import secrets
                    key_source = secrets.token_hex(32)
                    self.save_system_setting("credential_encryption_secret", key_source)

            key = hashlib.sha256(key_source.encode('utf-8')).digest()
            fernet_key = base64.urlsafe_b64encode(key)
            f = Fernet(fernet_key)
            return f.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
        except Exception as fernet_err:
            # Fallback to legacy XOR decryption
            try:
                from config import Config
                key_source = Config.SECRET_KEY or "fallback_secret_key_1234567890_!"
                import hashlib, base64
                key = hashlib.sha256(key_source.encode('utf-8')).digest()
                encrypted = base64.b64decode(encrypted_password.encode('utf-8'))
                decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
                return decrypted.decode('utf-8')
            except Exception as xor_err:
                logging.error(f"[Database] Error decrypting credential password: Fernet error: {fernet_err}, XOR error: {xor_err}", exc_info=True)
                return encrypted_password

    # ---- Inbound Reply Helper ----
    def record_inbound_reply(self, lead_id: int, user_id: int, sender_email: str, reply_text: str) -> bool:
        """Log incoming email reply and advance pipeline stage to REPLIED."""
        session = self.session
        try:
            log = MessageLogModel(
                lead_id=lead_id,
                user_id=user_id,
                template_used='email_reply',
                message_sent=reply_text,
                is_reply=True,
                reply_body=reply_text
            )
            session.add(log)

            lead = session.query(LeadModel).filter_by(id=lead_id, user_id=user_id).first()
            if lead:
                lead.pipeline_stage = 'REPLIED'
                lead.contacted = True
                lead.contact_date = utcnow()
                lead.drip_sequence_active = False
                lead.updated_at = utcnow()
            
            session.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error recording inbound reply for lead {lead_id}: {e}", exc_info=True)
            session.rollback()
            return False

    # ---- IMAP Settings Accessors ----
    def get_imap_settings(self, user_id: int) -> Optional[Dict]:
        """Fetch and decrypt IMAP mail configurations for a user."""
        session = self.session
        try:
            setting = session.query(ImapSettingsModel).filter_by(user_id=user_id).first()
            if not setting:
                return None
            res = to_dict(setting)
            res["password"] = self._decrypt_password(res.pop("imap_password_encrypted"))
            res["host"] = res.pop("imap_host")
            res["port"] = res.pop("imap_port")
            res["email"] = res.pop("imap_email")
            return res
        except Exception as e:
            logging.error(f"[Database] Error getting IMAP settings for user {user_id}: {e}", exc_info=True)
            return None

    def save_imap_settings(self, user_id: int, host: str, port: int, email: str, password_raw: str, use_ssl: bool) -> bool:
        """Encrypt and save IMAP mail configurations for a user."""
        session = self.session
        try:
            encrypted_pass = self._encrypt_password(password_raw)
            setting = session.query(ImapSettingsModel).filter_by(user_id=user_id).first()
            if not setting:
                setting = ImapSettingsModel(user_id=user_id)
                session.add(setting)
            setting.imap_host = host
            setting.imap_port = port
            setting.imap_email = email
            setting.imap_password_encrypted = encrypted_pass
            setting.use_ssl = use_ssl
            session.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving IMAP settings for user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    # ---- SMTP Settings Accessors ----
    def get_smtp_settings(self, user_id: int) -> Optional[Dict]:
        """Fetch and decrypt SMTP configurations for a user."""
        session = self.session
        try:
            setting = session.query(SmtpSettingsModel).filter_by(user_id=user_id).first()
            if not setting:
                return None
            res = to_dict(setting)
            res["password"] = self._decrypt_password(res.pop("smtp_password_encrypted"))
            res["host"] = res.pop("smtp_host")
            res["port"] = res.pop("smtp_port")
            res["email"] = res.pop("smtp_email")
            return res
        except Exception as e:
            logging.error(f"[Database] Error getting SMTP settings for user {user_id}: {e}", exc_info=True)
            return None

    def save_smtp_settings(self, user_id: int, host: str, port: int, email: str, password_raw: str, use_ssl: bool) -> bool:
        """Encrypt and save SMTP configurations for a user."""
        session = self.session
        try:
            encrypted_pass = self._encrypt_password(password_raw)
            setting = session.query(SmtpSettingsModel).filter_by(user_id=user_id).first()
            if not setting:
                setting = SmtpSettingsModel(user_id=user_id)
                session.add(setting)
            setting.smtp_host = host
            setting.smtp_port = port
            setting.smtp_email = email
            setting.smtp_password_encrypted = encrypted_pass
            setting.use_ssl = use_ssl
            session.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving SMTP settings for user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    # ---- Drip Configurations Accessors ----
    def get_drip_config(self, user_id: int) -> Optional[Dict]:
        """Fetch Drip Configuration settings for a user."""
        session = self.session
        try:
            setting = session.query(DripConfigurationsModel).filter_by(user_id=user_id).first()
            if not setting:
                return None
            return to_dict(setting)
        except Exception as e:
            logging.error(f"[Database] Error getting Drip configuration for user {user_id}: {e}", exc_info=True)
            return None

    def save_drip_config(self, user_id: int, delay_days: int, max_followups: int, followup_subject: str, followup_template: str, is_enabled: bool) -> bool:
        """Save Drip Configuration settings for a user."""
        session = self.session
        try:
            setting = session.query(DripConfigurationsModel).filter_by(user_id=user_id).first()
            if not setting:
                setting = DripConfigurationsModel(user_id=user_id)
                session.add(setting)
            setting.delay_days = delay_days
            setting.max_followups = max_followups
            setting.followup_subject = followup_subject
            setting.followup_template = followup_template
            setting.is_enabled = is_enabled
            session.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving Drip configuration for user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    # ---- User Portfolio Accessors ----
    def save_user_portfolio(self, user_id: int, portfolio_url: str, projects: list) -> bool:
        """Save a user's scanned portfolio URL and projects list into system_settings."""
        session = self.session
        try:
            # Save portfolio URL
            url_setting = session.query(SystemSettingsModel).filter_by(key=f"portfolio_url_{user_id}").first()
            if not url_setting:
                url_setting = SystemSettingsModel(key=f"portfolio_url_{user_id}", value=portfolio_url)
                session.add(url_setting)
            else:
                url_setting.value = portfolio_url
            
            # Save portfolio projects parsed JSON
            projects_setting = session.query(SystemSettingsModel).filter_by(key=f"portfolio_projects_{user_id}").first()
            projects_json = json.dumps(projects)
            if not projects_setting:
                projects_setting = SystemSettingsModel(key=f"portfolio_projects_{user_id}", value=projects_json)
                session.add(projects_setting)
            else:
                projects_setting.value = projects_json
                
            session.commit()
            return True
        except Exception as e:
            logging.error(f"[Database] Error saving portfolio for user {user_id}: {e}", exc_info=True)
            session.rollback()
            return False

    def get_user_portfolio(self, user_id: int) -> dict:
        """Retrieve a user's portfolio URL and scanned projects."""
        session = self.session
        try:
            url_setting = session.query(SystemSettingsModel).filter_by(key=f"portfolio_url_{user_id}").first()
            projects_setting = session.query(SystemSettingsModel).filter_by(key=f"portfolio_projects_{user_id}").first()
            
            url = url_setting.value if url_setting else ""
            projects = []
            if projects_setting and projects_setting.value:
                try:
                    projects = json.loads(projects_setting.value)
                except Exception:
                    pass
            return {"portfolio_url": url, "projects": projects}
        except Exception as e:
            logging.error(f"[Database] Error getting portfolio for user {user_id}: {e}", exc_info=True)
            return {"portfolio_url": "", "projects": []}

