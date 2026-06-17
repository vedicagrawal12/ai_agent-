import smtplib
import urllib.parse
import html
import re
import logging
import threading
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Dict, Optional
from database import Database

logger = logging.getLogger(__name__)

# Global thread references for drips scanning
_drip_thread = None
_drip_thread_lock = threading.Lock()
_drip_stop_event = threading.Event()

def format_followup_template(template: str, lead: Dict) -> str:
    """Format follow-up template body using lead parameters."""
    if not template:
        return ""
    replacements = {
        "{business_name}": lead.get("name", ""),
        "{city}": lead.get("city", ""),
        "{category}": lead.get("category", ""),
        "{rating}": str(lead.get("rating", 0.0)),
        "{reviews}": str(lead.get("reviews", 0)),
        "{website}": lead.get("website", ""),
        "{website_url}": lead.get("website", ""),
    }
    res = template
    for key, val in replacements.items():
        res = res.replace(key, val)
    return res

def process_drip_outreach_for_user(user_id: int):
    """Scan and dispatch auto-drip followups for unengaged CONTACTED leads."""
    db = Database()
    config = db.get_drip_config(user_id)
    if not config or not config.get("is_enabled"):
        return
        
    smtp_settings = db.get_smtp_settings(user_id)
    if not smtp_settings:
        logger.warning(f"[Drips] SMTP details not configured for user {user_id}. Skipping drip sequences.")
        return

    delay_days = config.get("delay_days", 3)
    max_followups = config.get("max_followups", 2)
    subject_template = config.get("followup_subject", "Quick follow up regarding proposal")
    body_template = config.get("followup_template")
    
    if not body_template:
        logger.warning(f"[Drips] Empty follow-up template for user {user_id}. Drips skipped.")
        return

    # Query leads needing auto-followup
    conn = db._get_connection()
    try:
        cursor = conn.cursor()
        # Match unengaged pitched leads
        cursor.execute("""
            SELECT id, name, email, city, category, rating, reviews, website, contacted, contact_date, last_followup_date, followup_count
            FROM leads
            WHERE user_id = %s 
              AND email IS NOT NULL AND email != ''
              AND contacted = TRUE
              AND pipeline_stage = 'PITCHED'
              AND drip_sequence_active = TRUE
              AND followup_count < %s
              AND COALESCE(last_followup_date, contact_date) <= CURRENT_TIMESTAMP - (INTERVAL '1 day' * %s);
        """, (user_id, max_followups, delay_days))
        leads = cursor.fetchall()
    except Exception as e:
        logger.error(f"[Drips] Error querying drip targets for user {user_id}: {e}")
        leads = []
    finally:
        db._release_connection(conn)

    if not leads:
        return

    logger.info(f"[Drips] Found {len(leads)} target leads matching drip conditions for user {user_id}")
    
    # SMTP details
    smtp_host = smtp_settings["host"]
    smtp_port = smtp_settings["port"]
    sender_email = smtp_settings["email"]
    smtp_password = smtp_settings["password"]
    use_ssl = smtp_settings.get("use_ssl", True)

    for lead_row in leads:
        lead = dict(lead_row)
        to_email = lead["email"].strip()
        lead_id = lead["id"]
        
        # Format templates
        subject = format_followup_template(subject_template, lead)
        body = format_followup_template(body_template, lead)
        
        # 1. Log outreach to obtain log_id
        log_id = 0
        try:
            log_id = db.log_message(lead_id, template=f"drip_followup_{lead['followup_count'] + 1}", message=body, user_id=user_id)
        except Exception as log_err:
            logger.error(f"[Drips] Error logging drip followup for lead {lead_id}: {log_err}")
            
        # 2. Format HTML and inject tracking pixel + link redirect wrapper
        html_body = html.escape(body)
        url_pattern = re.compile(r'(https?://[^\s<>"]+)')
        
        # Resolve a fallback base host. In background thread, request context is absent.
        # We can fetch server configuration or use local default.
        base_host = os.getenv("APP_URL", "http://localhost:5000").rstrip("/")
        
        def replace_url(match):
            url = match.group(1)
            clean_url = url
            trailing = ""
            while clean_url and clean_url[-1] in ".,;:!?()":
                trailing = clean_url[-1] + trailing
                clean_url = clean_url[:-1]
            if log_id:
                encoded_url = urllib.parse.quote(clean_url)
                tracking_url = f"{base_host}/api/track/click/{log_id}?dest={encoded_url}"
                return f'<a href="{tracking_url}" target="_blank">{clean_url}</a>{trailing}'
            return f'<a href="{clean_url}" target="_blank">{clean_url}</a>{trailing}'
            
        html_body = url_pattern.sub(replace_url, html_body)
        html_body = html_body.replace("\n", "<br>\n")
        
        if log_id:
            pixel_url = f"{base_host}/api/track/open/{log_id}"
            html_body += f'\n<img src="{pixel_url}" width="1" height="1" style="display:none;" alt="" />'

        # 3. Dispatch SMTP email
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            part1 = MIMEText(body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=10)
                server.ehlo()
                try:
                    server.starttls()
                    server.ehlo()
                except Exception as tls_err:
                    logger.debug(f"[Drips] SMTP STARTTLS failed: {tls_err}")
                    
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()
            
            # 4. Update lead tracking state
            new_count = lead["followup_count"] + 1
            # If we reached maximum allowed followups, turn off sequence
            sequence_active = new_count < max_followups
            
            conn = db._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE leads
                    SET last_followup_date = CURRENT_TIMESTAMP,
                        followup_count = %s,
                        drip_sequence_active = %s
                    WHERE id = %s
                """, (new_count, sequence_active, lead_id))
                conn.commit()
            finally:
                db._release_connection(conn)
            
            logger.info(f"[Drips] Successfully dispatched follow-up #{new_count} to {to_email} for lead {lead['name']}")
        except Exception as smtp_err:
            logger.error(f"[Drips] SMTP dispatch failed for lead {lead_id} to {to_email}: {smtp_err}")

def drip_background_poll_loop():
    """Background check loop polling once every hour."""
    logger.info("[Drips Background Daemon] Starting Drip sequencer thread...")
    db = Database()
    while not _drip_stop_event.is_set():
        try:
            # Query users having active auto-drips configurations
            conn = db._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT user_id FROM drip_configurations WHERE is_enabled = TRUE;")
                users = cursor.fetchall()
            finally:
                db._release_connection(conn)
            
            for user in users:
                user_id = user[0]
                process_drip_outreach_for_user(user_id)
        except Exception as e:
            logger.error(f"[Drips Background Daemon] Error in drip polling loop: {e}")
            
        # Poll once per hour (wake early if stop requested)
        # 3600 seconds = 1 hour
        for _ in range(3600):
            if _drip_stop_event.is_set():
                break
            time.sleep(1)

def start_drip_poller():
    """Start drip followups daemon thread."""
    global _drip_thread
    with _drip_thread_lock:
        if _drip_thread is None or not _drip_thread.is_alive():
            _drip_stop_event.clear()
            _drip_thread = threading.Thread(target=drip_background_poll_loop, name="DripSchedulerDaemon", daemon=True)
            _drip_thread.start()
            logger.info("[Drips Service] Background Drips scheduling thread started.")

def stop_drip_poller():
    """Request drip thread exit."""
    global _drip_thread
    with _drip_thread_lock:
        if _drip_thread is not None:
            _drip_stop_event.set()
            _drip_thread.join(timeout=2)
            _drip_thread = None
            logger.info("[Drips Service] Background Drips scheduling thread stopped.")
