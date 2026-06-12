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
@limiter.limit("5 per minute")
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
        
        subject = "Digital Storefront Design Proposal"
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
            "body": body
        })
    except Exception as e:
        return jsonify({"error": f"AI Generation failed: {str(e)}"}), 500

@outreach_bp.route("/outreach/send-smtp-email", methods=["POST"])
@limiter.limit("10 per hour")
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
        user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
        if not user_id:
            lead = db.get_lead_by_id(lead_id)
            if lead:
                user_id = lead.get('user_id')
        if not user_id:
            user_id = 1
        
        try:
            log_id = db.log_message(lead_id, template="cold_email", message=body, user_id=user_id)
        except Exception as db_err:
            logger.error(f"Error logging outreach message: {db_err}")

    # 2. HTML body conversion and link wrapping
    # Escape HTML to prevent injection
    html_body = html.escape(body)
    
    # Find all HTTP/HTTPS links
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
            return f'<a href="{tracking_url}" target="_blank">{clean_url}</a>{trailing}'
        else:
            return f'<a href="{clean_url}" target="_blank">{clean_url}</a>{trailing}'
            
    html_body = url_pattern.sub(replace_url, html_body)
    # Convert newlines to breaks
    html_body = html_body.replace("\n", "<br>\n")
    
    # Append tracking pixel if we have a log_id
    if log_id:
        pixel_url = f"{base_host}/api/track/open/{log_id}"
        html_body += f'\n<img src="{pixel_url}" width="1" height="1" style="display:none;" alt="" />'
    
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
        server.quit()
        
        if lead_id:
            # Enforce owner scope for stage update if user context is available
            user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
            db.update_lead_pipeline_stage(lead_id, "PITCHED", user_id=user_id)
            
        return jsonify({
            "success": True,
            "message": f"Email successfully dispatched directly to {to_email}!"
        })
    except Exception as e:
        logger.error(f"SMTP Delivery failed: {e}")
        return jsonify({"error": f"SMTP Delivery failed: {str(e)}"}), 500

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
    
    if not dest:
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
