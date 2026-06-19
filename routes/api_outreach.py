import logging
import smtplib
import html
import re
import urllib.parse
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify, g, send_file, redirect
from extensions import db, limiter
from utils.whatsapp import WhatsAppMessenger
from utils.ai_writer import AIOutreachWriter
from collectors.base_collector import Lead

logger = logging.getLogger(__name__)
outreach_bp = Blueprint('api_outreach', __name__)

@outreach_bp.route("/whatsapp/templates", methods=["GET"])
def get_whatsapp_templates():
    """Get available WhatsApp message templates."""
    templates = WhatsAppMessenger.get_templates()
    return jsonify({"success": True, "templates": templates})

@outreach_bp.route("/whatsapp/generate", methods=["POST"])
def generate_whatsapp_link():
    """
    Generate a WhatsApp link with personalized message.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    phone = data.get("phone", "")
    template_key = data.get("template", "website_pitch")
    custom_message = data.get("custom_message", "")
    lead_data = data.get("lead", {})
    
    if not phone:
        return jsonify({"error": "Phone number is required"}), 400
    
    lead = Lead(
        name=lead_data.get("name", ""),
        phone=lead_data.get("phone", ""),
        address=lead_data.get("address", ""),
        rating=lead_data.get("rating", 0),
        reviews=lead_data.get("reviews", 0),
        category=lead_data.get("category", ""),
        city=lead_data.get("city", ""),
        whatsapp_number=phone
    )
    
    message = WhatsAppMessenger.build_message(template_key, lead, custom_message)
    link = WhatsAppMessenger.generate_whatsapp_link(phone, message)
    
    lead_id = lead_data.get("id")
    if lead_id:
        # Enforce that the lead belongs to the logged-in user
        user_lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
        if not user_lead:
            return jsonify({"error": "Lead not found"}), 404
            
        try:
            db.log_message(lead_id, template_key, message, user_id=g.user['id'])
        except Exception as log_err:
            logger.error(f"Error logging WhatsApp message to DB: {log_err}")
            
    return jsonify({
        "success": True,
        "whatsapp_link": link,
        "message": message
    })

@outreach_bp.route("/outreach/generate-ai", methods=["POST"])
@limiter.limit("5 per minute")
def generate_ai_pitch():
    """
    Generate a unique, highly personalized outreach pitch using Gemini API.
    """
    gemini_key = request.headers.get("X-Gemini-API-Key")
    if not gemini_key:
        return jsonify({"error": "Gemini API key is missing. Please configure it in Settings."}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    lead_data = data.get("lead", {})
    project_sample = data.get("project_sample", "")
    tone = data.get("tone", "elite")
    length = data.get("length", "detailed")
    service = data.get("service", "web_design")
    sender = data.get("sender", {})
    refine_feedback = data.get("refine_feedback")
    previous_pitch = data.get("previous_pitch")
    custom_pitch_rules = data.get("custom_pitch_rules", "")
    min_words = data.get("min_words", 150)
    language = data.get("language", "hinglish")
    
    if not lead_data:
        return jsonify({"error": "Lead data is required"}), 400
        
    try:
        sender_name = sender.get("name", "")
        sender_brand = sender.get("brand", "")
        base_host = request.host_url.rstrip('/')
        lead_id = lead_data.get("id")
        
        mockup_link = ""
        audit_link = ""
        audit_data = None
        if lead_id:
            mockup_link = f"{base_host}/preview/{lead_id}?sender_name={sender_name}&sender_brand={sender_brand}"
            lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
            if lead:
                lead_data = dict(lead)
                audit_data_str = lead.get("audit_data", "")
                if audit_data_str:
                    try:
                        import json
                        audit_data = json.loads(audit_data_str)
                        audit_link = f"{base_host}/audit/{lead_id}"
                    except Exception as e:
                        logger.error(f"Error parsing audit data: {e}")
  
        pitch = AIOutreachWriter.generate_pitch(
            lead_data=lead_data,
            project_sample=project_sample,
            api_key=gemini_key,
            tone=tone,
            length=length,
            service=service,
            sender_info=sender,
            refine_feedback=refine_feedback,
            previous_pitch=previous_pitch,
            mockup_link=mockup_link,
            custom_pitch_rules=custom_pitch_rules,
            min_words=min_words,
            language=language,
            audit_link=audit_link,
            audit_data=audit_data
        )
        
        lead_id = lead_data.get("id")
        if lead_id:
            db.update_lead_pitch(lead_id, pitch, user_id=g.user['id'])
            
        return jsonify({
            "success": True,
            "pitch": pitch
        })
    except Exception as e:
        return jsonify({"error": f"AI Generation failed: {str(e)}"}), 500


@outreach_bp.route("/outreach/generate-email-ai", methods=["POST"])
@limiter.limit("30 per minute")
def generate_email_ai_pitch():
    """Statelessly compile an AI cold email using Gemini."""
    gemini_key = request.headers.get("X-Gemini-API-Key")
    if not gemini_key:
        return jsonify({"error": "Gemini API key is missing. Please configure it in Settings."}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    lead_data = data.get("lead", {})
    project_sample = data.get("project_sample", "")
    tone = data.get("tone", "elite")
    service = data.get("service", "web_design")
    sender = data.get("sender", {})
    custom_pitch_rules = data.get("custom_pitch_rules", "")
    min_words = data.get("min_words", 150)
    language = data.get("language", "hinglish")
    
    if not lead_data:
        return jsonify({"error": "Lead data is required"}), 400
        
    try:
        sender_name = sender.get("name", "")
        sender_brand = sender.get("brand", "")
        base_host = request.host_url.rstrip('/')
        lead_id = lead_data.get("id")
        
        mockup_link = ""
        audit_link = ""
        audit_data = None
        if lead_id:
            mockup_link = f"{base_host}/preview/{lead_id}?sender_name={sender_name}&sender_brand={sender_brand}"
            lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
            if lead:
                lead_data = dict(lead)
                audit_data_str = lead.get("audit_data", "")
                if audit_data_str:
                    try:
                        import json
                        audit_data = json.loads(audit_data_str)
                        audit_link = f"{base_host}/audit/{lead_id}"
                    except Exception as e:
                        logger.error(f"Error parsing audit data: {e}")
            
        # If autopilot is active, dynamically determine the best service
        autopilot = data.get("autopilot", False)
        if autopilot:
            has_no_site = not lead_data.get("website", "").strip()
            is_broken = bool(lead_data.get("is_broken_website", False))
            if has_no_site or is_broken:
                service = "web_design"
            else:
                service = "seo"

        raw_pitch = AIOutreachWriter.generate_email_pitch(
            lead_data=lead_data,
            project_sample=project_sample,
            api_key=gemini_key,
            tone=tone,
            service=service,
            sender_info=sender,
            mockup_link=mockup_link,
            custom_pitch_rules=custom_pitch_rules,
            min_words=min_words,
            language=language,
            audit_link=audit_link,
            audit_data=audit_data
        )
        
        subject_map = {
            'web_design': 'Digital Storefront Design Proposal',
            'seo': 'SEO & Google Ranking Growth Proposal',
            'social_media': 'Social Media Branding Proposal',
            'gmb': 'Google Business Profile Optimization Proposal'
        }
        subject = subject_map.get(service, 'Business Growth & Digital Services Proposal')
        body = raw_pitch
        
        if "BODY:" in raw_pitch:
            parts = raw_pitch.split("BODY:")
            subject_part = parts[0].replace("SUBJECT:", "").strip()
            if subject_part:
                subject = subject_part
            body = parts[1].strip()
        elif "SUBJECT:" in raw_pitch:
            subject_part = raw_pitch.replace("SUBJECT:", "").strip()
            if "\n" in subject_part:
                subject = subject_part.split("\n")[0].strip()
                body = "\n".join(subject_part.split("\n")[1:]).strip()
        
        return jsonify({
            "success": True,
            "subject": subject,
            "body": body,
            "resolved_service": service
        })
    except Exception as e:
        return jsonify({"error": f"AI Generation failed: {str(e)}"}), 500

@outreach_bp.route("/outreach/send-smtp-email", methods=["POST"])
@limiter.limit("120 per hour")
def send_smtp_email():
    """Send cold email statelessly using user SMTP details, wrapping links for tracking."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    to_email = data.get("to_email", "").strip()
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()
    smtp_config = data.get("smtp_config", {})
    lead_id = data.get("lead_id")
    
    if not to_email or not subject or not body:
        return jsonify({"error": "Missing recipient, subject, or body details."}), 400
        
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    if lead_id:
        # Enforce that the lead belongs to the logged-in user
        lead = db.get_lead_by_id(lead_id, user_id=user_id)
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
            
    smtp_host = smtp_config.get("host", "").strip()
    smtp_port = smtp_config.get("port")
    sender_email = smtp_config.get("email", "").strip()
    smtp_password = smtp_config.get("password", "").strip()
    use_ssl = smtp_config.get("use_ssl", False)
    
    if not smtp_host or not smtp_port or not sender_email or not smtp_password:
        return jsonify({"error": "Complete SMTP credentials are required to send direct email."}), 400
    
    # 1. Log the message to get a log_id
    log_id = 0
    if lead_id:
        try:
            log_id = db.log_message(lead_id, template="cold_email", message=body, user_id=user_id)
        except Exception as db_err:
            logger.error(f"Error logging outreach message: {db_err}")
        
        if not log_id:
            logger.warning(f"Email tracking degraded: log_id=0 for lead {lead_id}. Open/click tracking and View Message will be unavailable.")

    # 2. HTML body conversion and link wrapping
    # IMPORTANT: Extract and wrap URLs from plain text FIRST, then escape
    # non-URL text. This prevents html.escape() from mangling & -> &amp;
    # inside URL query parameters, which would break tracked redirect links.
    url_pattern = re.compile(r'(https?://[^\s<>"]+)')
    base_host = request.host_url.rstrip('/')
    
    def replace_url(match):
        url = match.group(1)
        # Strip trailing punctuation that is not part of the URL
        clean_url = url
        trailing = ""
        while clean_url and clean_url[-1] in ".,;:!?()":
            trailing = clean_url[-1] + trailing
            clean_url = clean_url[:-1]
            
        if log_id:
            encoded_url = urllib.parse.quote(clean_url)
            tracking_url = f"{base_host}/api/track/click/{log_id}?dest={encoded_url}"
            return f'\x00LINK_START\x00<a href="{tracking_url}" target="_blank">{html.escape(clean_url)}</a>{html.escape(trailing)}\x00LINK_END\x00'
        else:
            return f'\x00LINK_START\x00<a href="{clean_url}" target="_blank">{html.escape(clean_url)}</a>{html.escape(trailing)}\x00LINK_END\x00'
    
    # Replace URLs with sentinel-wrapped HTML links
    marked_body = url_pattern.sub(replace_url, body)
    
    # Split by sentinels, escape text segments only, reassemble
    parts = re.split(r'\x00LINK_START\x00|\x00LINK_END\x00', marked_body)
    html_segments = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Text segment — escape HTML
            html_segments.append(html.escape(part))
        else:
            # Link segment — already HTML, keep as-is
            html_segments.append(part)
    html_body = ''.join(html_segments)
    
    # Convert newlines to breaks
    html_body = html_body.replace("\n", "<br>\n")
    
    # Append tracking pixel if we have a log_id
    if log_id:
        pixel_url = f"{base_host}/api/track/open/{log_id}"
        html_body += f'\n<img src="{pixel_url}" width="1" height="1" style="display:none;" alt="" />'
        try:
            # Store subject alongside HTML so telemetry "View Message" can display it
            stored_content = f"SUBJECT:{subject}\n{html_body}"
            db.update_message_content(log_id, stored_content)
        except Exception as update_err:
            logger.error(f"Error updating message log content with HTML: {update_err}")
    
    server = None
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        part1 = MIMEText(body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        port = int(smtp_port)
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=10)
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception as tls_err:
                logger.warning(f"STARTTLS failed: {tls_err}")
                
        server.login(sender_email, smtp_password)
        server.sendmail(sender_email, [to_email], msg.as_string())
        
        if lead_id:
            # Enforce owner scope for stage update if user context is available
            db.update_lead_pipeline_stage(lead_id, "PITCHED", user_id=user_id)
            
        return jsonify({
            "success": True,
            "message": f"Email successfully dispatched directly to {to_email}!"
        })
    except Exception as e:
        logger.error(f"SMTP Delivery failed: {e}")
        return jsonify({"error": f"SMTP Delivery failed: {str(e)}"}), 500
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass

@outreach_bp.route("/track/open/<int:log_id>", methods=["GET"])
@limiter.limit("30 per minute")
def track_open(log_id):
    """Track email open event and return a 1x1 transparent pixel."""
    try:
        db.record_email_open(log_id)
    except Exception as e:
        logger.error(f"Error tracking open for log {log_id}: {e}")
    
    # 1x1 transparent GIF
    pixel_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return send_file(BytesIO(pixel_data), mimetype='image/gif')

@outreach_bp.route("/track/click/<int:log_id>", methods=["GET"])
@limiter.limit("20 per minute")
def track_click(log_id):
    """Track link click and redirect to the destination URL."""
    dest = request.args.get('dest', '').strip()
    lead_id = 0
    try:
        lead_id = db.record_link_click(log_id, dest)
        if lead_id:
            # Automatically advance the lead's pipeline stage to INTERESTED
            # Since click occurs outside user session, update without scoping to user
            db.update_lead_pipeline_stage(lead_id, "INTERESTED")
    except Exception as e:
        logger.error(f"Error tracking click for log {log_id}: {e}")
    
    # Validate destination URL to prevent open redirect attacks
    if not dest:
        dest = "/"
    else:
        parsed = urllib.parse.urlparse(dest)
        # Only allow http/https schemes, block javascript:, data:, etc.
        if parsed.scheme and parsed.scheme.lower() not in ('http', 'https'):
            logger.warning(f"Blocked suspicious redirect scheme: {parsed.scheme} for dest={dest}")
            dest = "/"
        # Block URLs with embedded credentials (user:pass@evil.com)
        if '@' in (parsed.netloc or ''):
            logger.warning(f"Blocked redirect with embedded credentials: dest={dest}")
            dest = "/"
        
    return redirect(dest)

@outreach_bp.route("/config/imap", methods=["GET", "POST"])
def manage_imap_config():
    """Save or retrieve IMAP configuration settings for the user."""
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == "POST":
        data = request.get_json() or {}
        host = data.get("host", "").strip()
        port = data.get("port")
        email_addr = data.get("email", "").strip()
        password = data.get("password", "").strip()
        use_ssl = data.get("use_ssl", True)
        
        if not host or not port or not email_addr or not password:
            return jsonify({"error": "Missing required IMAP settings"}), 400
            
        try:
            port = int(port)
        except ValueError:
            return jsonify({"error": "Invalid port number"}), 400
            
        # Preserve existing password if the submitted one is masked
        is_masked = password == "****" or (len(password) > 2 and password[2:] == "*" * (len(password) - 2))
        if is_masked:
            existing = db.get_imap_settings(user_id)
            if existing and existing.get("password"):
                password = existing["password"]
            
        success = db.save_imap_settings(user_id, host, port, email_addr, password, use_ssl)
        if success:
            return jsonify({"success": True, "message": "IMAP credentials saved successfully."})
        return jsonify({"error": "Failed to save IMAP credentials."}), 500
        
    else:
        # GET request
        settings = db.get_imap_settings(user_id)
        if not settings:
            return jsonify({"configured": False})
        
        # Mask the decrypted password
        password = settings.get("password", "")
        masked_password = password[:2] + "*" * (len(password) - 2) if len(password) > 2 else "****"
        settings["password"] = masked_password
        settings["configured"] = True
        return jsonify(settings)

@outreach_bp.route("/config/smtp", methods=["GET", "POST"])
def manage_smtp_config():
    """Save or retrieve SMTP configuration settings for the user."""
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == "POST":
        data = request.get_json() or {}
        host = data.get("host", "").strip()
        port = data.get("port")
        email_addr = data.get("email", "").strip()
        password = data.get("password", "").strip()
        use_ssl = data.get("use_ssl", True)
        
        if not host or not port or not email_addr or not password:
            return jsonify({"error": "Missing required SMTP settings"}), 400
            
        try:
            port = int(port)
        except ValueError:
            return jsonify({"error": "Invalid port number"}), 400
            
        # Preserve existing password if the submitted one is masked
        is_masked = password == "****" or (len(password) > 2 and password[2:] == "*" * (len(password) - 2))
        if is_masked:
            existing = db.get_smtp_settings(user_id)
            if existing and existing.get("password"):
                password = existing["password"]
            
        success = db.save_smtp_settings(user_id, host, port, email_addr, password, use_ssl)
        if success:
            return jsonify({"success": True, "message": "SMTP credentials saved successfully."})
        return jsonify({"error": "Failed to save SMTP credentials."}), 500
        
    else:
        # GET request
        settings = db.get_smtp_settings(user_id)
        if not settings:
            return jsonify({"configured": False})
        
        password = settings.get("password", "")
        masked_password = password[:2] + "*" * (len(password) - 2) if len(password) > 2 else "****"
        settings["password"] = masked_password
        settings["configured"] = True
        return jsonify(settings)

@outreach_bp.route("/outreach/sync-replies", methods=["POST"])
def sync_replies():
    """Manually trigger IMAP synchronization for incoming email replies."""
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    from utils.imap_reader import sync_user_replies
    res = sync_user_replies(user_id)
    if res.get("success"):
        return jsonify(res)
    return jsonify({"error": res.get("error", "Unknown sync error")}), 500

@outreach_bp.route("/outreach/recent-delivered", methods=["GET"])
def get_recent_delivered_emails():
    """Retrieve all emails sent in the last 12 hours."""
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        logs = db.get_recent_delivered_emails(user_id, hours=12)
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        logger.error(f"Error fetching recent logs: {e}")
        return jsonify({"error": str(e)}), 500
