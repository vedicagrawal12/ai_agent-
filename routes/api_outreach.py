import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify, g
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
        if lead_id:
            mockup_link = f"{base_host}/preview/{lead_id}?sender_name={sender_name}&sender_brand={sender_brand}"
  
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
            language=language
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
        if lead_id:
            mockup_link = f"{base_host}/preview/{lead_id}?sender_name={sender_name}&sender_brand={sender_brand}"
            
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
            language=language
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
    """Send cold email statelessly using user SMTP details."""
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
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
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
            db.update_lead_pipeline_stage(lead_id, "PITCHED", user_id=g.user['id'])
            
        return jsonify({
            "success": True,
            "message": f"Email successfully dispatched directly to {to_email}!"
        })
    except Exception as e:
        return jsonify({"error": f"SMTP Delivery failed: {str(e)}"}), 500
