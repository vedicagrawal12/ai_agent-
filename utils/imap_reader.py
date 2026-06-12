import imaplib
import email
from email.header import decode_header
import re
import logging
import threading
import time
from typing import Dict, List, Optional
from database import Database

logger = logging.getLogger(__name__)

# Global thread reference for background scanning
_bg_thread = None
_bg_thread_lock = threading.Lock()
_bg_stop_event = threading.Event()

def clean_email_address(from_header: str) -> str:
    """Extract clean email address from From header, e.g. 'John Doe <john@example.com>' -> 'john@example.com'"""
    if not from_header:
        return ""
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).strip().lower()
    return from_header.strip().lower()

def decode_mime_header(header_value) -> str:
    """Decode MIME header values safely."""
    if not header_value:
        return ""
    try:
        decoded_fragments = decode_header(header_value)
        value_parts = []
        for text, encoding in decoded_fragments:
            if isinstance(text, bytes):
                value_parts.append(text.decode(encoding or 'utf-8', errors='ignore'))
            else:
                value_parts.append(str(text))
        return "".join(value_parts)
    except Exception as e:
        logger.debug(f"[IMAP] Header decode warning: {e}")
        return str(header_value)

def parse_email_body(msg) -> str:
    """Extract plain text payload from MIME message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disp = str(part.get('Content-Disposition'))
            if content_type == 'text/plain' and 'attachment' not in content_disp:
                try:
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        except Exception:
            pass
    return body.strip()

def sync_user_replies(user_id: int) -> Dict:
    """Connect to IMAP server, poll inbox, match sender to leads list, and save replies."""
    db = Database()
    settings = db.get_imap_settings(user_id)
    if not settings:
        return {"success": False, "error": "IMAP credentials not configured under settings."}

    host = settings["host"]
    port = settings["port"]
    email_user = settings["email"]
    password = settings["password"]
    use_ssl = settings.get("use_ssl", True)

    logger.info(f"[IMAP] Syncing replies for user {user_id} using host {host}:{port} ({email_user})")
    
    mail = None
    replies_found = 0
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
            
        mail.login(email_user, password)
        mail.select("INBOX")
        
        # Search for unread/unseen emails
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            return {"success": False, "error": "Failed to search mailbox."}
            
        msg_ids = data[0].split()
        if not msg_ids:
            return {"success": True, "replies_synced": 0, "message": "No new unread messages."}
            
        # Get active leads email mappings
        conn = db._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, name FROM leads WHERE user_id = %s AND email IS NOT NULL AND email != '';", (user_id,))
            leads_list = cursor.fetchall()
        finally:
            db._release_connection(conn)
        
        # Map clean email address to lead dict details
        leads_map = {l['email'].strip().lower(): l for l in leads_list if l['email']}
        
        for msg_id in msg_ids:
            # Fetch message envelope and headers without marking it as seen/read
            res, msg_data = mail.fetch(msg_id, "(BODY.PEEK[])")
            if res != "OK":
                continue
                
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract header info
                    raw_from = msg.get("From", "")
                    from_email = clean_email_address(decode_mime_header(raw_from))
                    
                    # Check if the sender matches one of our active leads
                    if from_email in leads_map:
                        lead = leads_map[from_email]
                        reply_text = parse_email_body(msg)
                        if not reply_text:
                            reply_text = f"Email reply received from {from_email} (unreadable or empty body)."
                            
                        # Save the reply and update pipeline stage to REPLIED
                        db.record_inbound_reply(lead['id'], user_id, from_email, reply_text)
                        replies_found += 1
                        logger.info(f"[IMAP] Sync matched email reply from {from_email} for lead {lead['name']}")
                        
                        # Mark email as read/seen on the server
                        mail.store(msg_id, "+FLAGS", "\\Seen")

        # Update last synced at timestamp in settings
        conn = db._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE imap_settings SET last_synced_at = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
            conn.commit()
        finally:
            db._release_connection(conn)
        
        return {"success": True, "replies_synced": replies_found}
    except Exception as e:
        logger.error(f"[IMAP] Error during mailbox sync for user {user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass

def background_poll_loop():
    """Continuous daemon loop running in the background polling every 5 minutes."""
    logger.info("[IMAP Background Daemon] Starting IMAP reader poller loop thread...")
    db = Database()
    while not _bg_stop_event.is_set():
        try:
            # Fetch users who have IMAP settings configured
            conn = db._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT user_id FROM imap_settings;")
                users = cursor.fetchall()
            finally:
                db._release_connection(conn)
            
            for user in users:
                user_id = user[0]
                sync_user_replies(user_id)
        except Exception as e:
            logger.error(f"[IMAP Background Daemon] Error in background polling thread: {e}")
            
        # Sleep for 5 minutes (or wake early if stop requested)
        for _ in range(300):
            if _bg_stop_event.is_set():
                break
            time.sleep(1)

def start_background_poller():
    """Start the background thread loop if not already running."""
    global _bg_thread
    with _bg_thread_lock:
        if _bg_thread is None or not _bg_thread.is_alive():
            _bg_stop_event.clear()
            _bg_thread = threading.Thread(target=background_poll_loop, name="IMAPReaderDaemon", daemon=True)
            _bg_thread.start()
            logger.info("[IMAP Service] Background email sync thread started successfully.")

def stop_background_poller():
    """Request the background poller thread to exit."""
    global _bg_thread
    with _bg_thread_lock:
        if _bg_thread is not None:
            _bg_stop_event.set()
            _bg_thread.join(timeout=2)
            _bg_thread = None
            logger.info("[IMAP Service] Background email sync thread stopped.")
