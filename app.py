"""
AI Lead Generation Agent — Main Flask Application

A powerful tool for finding local businesses on Google Maps that need
websites and online presence. Supports WhatsApp outreach with
personalized message templates.

Built with an extensible architecture for future platform integrations
(Instagram, Facebook, JustDial, etc.).

Usage:
    1. Set your Google Places API key in .env or through the dashboard
    2. Run: python app.py
    3. Open: http://localhost:5000
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, Response, send_file, session, redirect, url_for, flash, g
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from collectors.serpapi_collector import SerpApiCollector
from utils.data_cleaner import DataCleaner
from utils.whatsapp import WhatsAppMessenger
from utils.portfolio import PortfolioParser
from utils.ai_writer import AIOutreachWriter
from database import Database

# Load environment variables
load_dotenv()

# Initialize components
collector = SerpApiCollector()

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32).hex()

# BUG-M7 fix: CSRF protection via SameSite cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# BUG-M3 fix: Custom JSON encoder to handle datetime objects from PostgreSQL
import json
class SafeJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)
app.json_encoder = SafeJSONEncoder

# Initialize database
db = Database()

# Store API key in memory (loaded from .env or set via API)
API_KEY_STORE = {
    "serpapi": os.getenv("SERPAPI_KEY", "")
}


# ============================================================
# Authentication Middleware
# ============================================================

@app.before_request
def handle_authentication():
    # 1. Load current user into g.user
    user_id = session.get('user_id')
    g.user = {"id": user_id, "username": session.get('username')} if user_id else None
    
    # 2. Check path / endpoint permission
    # Public endpoints (allowing 'index' root route and 'verify_db' diagnostics to be accessed without login)
    if request.endpoint in ['login', 'signup', 'live_preview_mockup', 'static', 'index']:
        return
        
    if request.path == '/' or request.path.startswith('/login') or request.path.startswith('/signup') or request.path.startswith('/preview/') or request.path.startswith('/static/'):
        return
        
    if not g.user:
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized. Please login."}), 401
        return redirect(url_for('login'))


# ============================================================
# Page Routes & Auth Handlers
# ============================================================

@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


@app.route("/verify-db")
def verify_db():
    """Check database connection and schemas, and render diagnostic dashboard."""
    status_info = {}
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Get server version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        status_info["version"] = version
        status_info["connection"] = "HEALTHY"
        
        # Check tables existence and count rows
        tables = ["users", "leads", "search_history", "message_log"]
        table_statuses = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                table_statuses[table] = {
                    "exists": True,
                    "status": "HEALTHY",
                    "rows": count
                }
            except Exception as tbl_err:
                conn.rollback() # reset aborted transaction block
                table_statuses[table] = {
                    "exists": False,
                    "status": "ERROR",
                    "error": str(tbl_err)
                }
                
        status_info["tables"] = table_statuses
        
        # Fetch registered users list safely
        users_list = []
        if table_statuses.get("users", {}).get("exists"):
            try:
                cursor.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at DESC;")
                for row in cursor.fetchall():
                    user_dict = dict(row)
                    if user_dict.get("created_at"):
                        user_dict["created_at_str"] = user_dict["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        user_dict["created_at_str"] = "N/A"
                    users_list.append(user_dict)
            except Exception as users_err:
                conn.rollback()
                print(f"Error fetching users list: {users_err}")
        status_info["users_list"] = users_list
        
        status_info["error"] = None
        conn.close()
    except Exception as e:
        status_info["connection"] = "FAILED"
        status_info["error"] = str(e)
        status_info["tables"] = {}
        status_info["version"] = "N/A"
        status_info["users_list"] = []
        
    return render_template("db_status.html", status=status_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for('index'))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")
            
        user = db.get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect(url_for('index'))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not username or not email or not password:
            flash("Username, email, and password are required.", "error")
            return render_template("signup.html")
        
        # BUG-H2 fix: Validate email format
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Please enter a valid email address (e.g. name@example.com).", "error")
            return render_template("signup.html")
        
        # BUG-H3 fix: Enforce password strength
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("signup.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
            
        # Check if user already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            flash("Username already exists.", "error")
            return render_template("signup.html")
            
        # Create user
        password_hash = generate_password_hash(password)
        success = db.create_user(username, email, password_hash)
        if success:
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Failed to create account. Please try again.", "error")
            
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))


# ============================================================
# API Routes — Search & Leads
# ============================================================

def enrich_lead_dict(lead, db_leads_dict):
    lead_dict = lead.to_dict()
    db_lead = db_leads_dict.get(lead.place_id)
    if db_lead:
        lead_dict['id'] = db_lead['id']
        lead_dict['instagram'] = db_lead.get('instagram') or ''
        lead_dict['facebook'] = db_lead.get('facebook') or ''
        lead_dict['custom_pitch'] = db_lead.get('custom_pitch') or ''
        # Prefer in-memory values for freshly-scanned fields, fall back to DB
        if not lead_dict.get('is_broken_website'):
            lead_dict['is_broken_website'] = db_lead.get('is_broken_website', 0) or 0
        if not lead_dict.get('line_type'):
            lead_dict['line_type'] = db_lead.get('line_type') or ''
    else:
        lead_dict['id'] = None
        lead_dict['instagram'] = ''
        lead_dict['facebook'] = ''
        lead_dict['custom_pitch'] = ''
    return lead_dict


@app.route("/api/search", methods=["POST"])
def search_businesses():
    """
    Search Google Maps for businesses.
    
    Request body:
        {
            "query": "gym",
            "city": "bhopal",
            "max_results": 20,
            "include_with_website": false
        }
    
    Returns filtered and cleaned leads.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    query = data.get("query", "").strip()
    city = data.get("city", "").strip()
    max_results = data.get("max_results", 20)
    include_with_website = data.get("include_with_website", False)
    hide_saved = data.get("hide_saved", False)
    deep_scan = data.get("deep_scan", False)
    zones = data.get("zones", [])
    if isinstance(zones, list):
        # Limit to max 10 zones to prevent API credit abuse (BUG-L8)
        zones = zones[:10]
    else:
        zones = []
    start_offset = data.get("start_offset", 0)
    
    if not query:
        return jsonify({"error": "Please enter a business type/keyword"}), 400
    
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400
    
    # Check API key (use X-SerpApi-Key header if provided, otherwise fallback to server key)
    api_key = request.headers.get("X-SerpApi-Key") or API_KEY_STORE.get("serpapi", "")
    if not api_key:
        return jsonify({"error": "SerpApi key not configured. Please set it in Settings."}), 401
    
    try:
        # Get already saved place IDs if hide_saved is enabled
        exclude_place_ids = set()
        if hide_saved:
            conn = None
            try:
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT place_id FROM leads WHERE user_id = %s AND place_id IS NOT NULL AND place_id != ''", (g.user['id'],))
                exclude_place_ids = {row[0] for row in cursor.fetchall()}
            except Exception as db_err:
                print(f"Error fetching saved place IDs: {db_err}")
            finally:
                if conn:
                    conn.close()

        # Search for businesses
        all_leads = []
        if deep_scan and zones:
            # We want to scan multiple zones
            # Compute max results to fetch per zone
            leads_per_zone = max(10, max_results // len(zones))
            
            for zone in zones:
                zone = zone.strip()
                if not zone:
                    continue
                # BUG-H1 fix: Always start at offset 0 for each zone in deep scan
                # (pagination offset only applies to single-city search)
                zone_leads = collector.search(query, f"{zone}, {city}", leads_per_zone, exclude_place_ids, 0, api_key=api_key)
                all_leads.extend(zone_leads)
                # BUG-H3 fix: Update exclude set with newly found place_ids
                # to avoid fetching the same business across zone boundaries
                for zl in zone_leads:
                    if zl.place_id:
                        exclude_place_ids.add(zl.place_id)
        else:
            # Standard single-city search
            all_leads = collector.search(query, city, max_results, exclude_place_ids, start_offset, api_key=api_key)
        
        # Clean the data (standardize, assign priority, and DEDUPLICATE combined leads)
        all_leads = DataCleaner.clean_leads(all_leads)
        
        # Filter out businesses with websites (unless requested)
        filtered_leads = DataCleaner.filter_leads(all_leads, include_with_website)
        
        # BUG-H2 fix: Save ALL discovered leads to database BEFORE capping the response
        db.save_leads(all_leads, user_id=g.user['id'])
        
        # Cap to max_results to match the requested amount for the API response
        filtered_leads = filtered_leads[:max_results]
        all_leads = all_leads[:max_results]
        
        search_query_log = f"{query} (Deep Scan)" if deep_scan else query
        db.save_search(search_query_log, city, len(all_leads), len(filtered_leads), user_id=g.user['id'])
        
        # Fetch the saved leads from DB to get database IDs and social links
        db_leads_dict = {}
        conn = None
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            place_ids = [l.place_id for l in all_leads if l.place_id]
            if place_ids:
                placeholders = ",".join("%s" for _ in place_ids)
                cursor.execute(f"SELECT * FROM leads WHERE user_id = %s AND place_id IN ({placeholders})", [g.user['id']] + place_ids)
                db_leads_dict = {row['place_id']: dict(row) for row in cursor.fetchall()}
        except Exception as db_err:
            print(f"Error fetching database IDs for search response: {db_err}")
        finally:
            if conn:
                conn.close()

        # Build response (BUG-L4)
        leads_data = [enrich_lead_dict(l, db_leads_dict) for l in filtered_leads]
        all_data = [enrich_lead_dict(l, db_leads_dict) for l in all_leads]
        
        # Calculate stats
        stats = {
            "total_found": len(all_leads),
            "leads_count": len(filtered_leads),
            "ignored_count": len(all_leads) - len(filtered_leads),
            "high_priority": sum(1 for l in filtered_leads if l.priority == "HIGH"),
            "medium_priority": sum(1 for l in filtered_leads if l.priority == "MEDIUM"),
            "low_priority": sum(1 for l in filtered_leads if l.priority == "LOW"),
            "with_phone": sum(1 for l in filtered_leads if l.phone),
            "with_whatsapp": sum(1 for l in filtered_leads if l.whatsapp_number),
            "broken_websites": sum(1 for l in filtered_leads if l.is_broken_website == 1),
        }
        
        return jsonify({
            "success": True,
            "leads": leads_data,
            "all_results": all_data,
            "stats": stats,
            "query": f"{query} in {city}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/leads", methods=["GET"])
def get_saved_leads():
    """Get all saved leads from the database."""
    priority = request.args.get("priority")
    city = request.args.get("city")
    
    leads = db.get_all_leads(priority_filter=priority, city_filter=city, user_id=g.user['id'])
    return jsonify({"success": True, "leads": leads})


@app.route("/api/leads/<int:lead_id>/contact", methods=["POST"])
def mark_lead_contacted(lead_id):
    """Mark a lead as contacted."""
    data = request.get_json() or {}
    notes = data.get("notes", "")
    
    db.mark_contacted(lead_id, notes, user_id=g.user['id'])
    return jsonify({"success": True, "message": "Lead marked as contacted"})


@app.route("/api/leads/<int:lead_id>/pipeline", methods=["POST"])
def update_lead_pipeline(lead_id):
    """Update lead pipeline stage."""
    data = request.get_json() or {}
    stage = data.get("stage", "NEW").upper()
    
    if stage not in ["NEW", "PITCHED", "INTERESTED", "CONVERTED", "IGNORED"]:
        return jsonify({"error": "Invalid pipeline stage"}), 400
        
    success = db.update_lead_pipeline_stage(lead_id, stage, user_id=g.user['id'])
    if success:
        return jsonify({"success": True, "message": f"Lead pipeline updated to {stage}", "stage": stage})
    else:
        return jsonify({"error": "Failed to update pipeline stage"}), 500


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    """Delete a lead."""
    db.delete_lead(lead_id, user_id=g.user['id'])
    return jsonify({"success": True, "message": "Lead deleted"})


@app.route("/api/leads/<int:lead_id>/schedule-reminder", methods=["POST"])
def schedule_lead_reminder(lead_id):
    """Schedule a follow-up reminder for a lead."""
    data = request.get_json() or {}
    days = data.get("days")
    custom_date = data.get("custom_date")
    
    if days is not None:
        try:
            from datetime import date, timedelta
            remind_date = (date.today() + timedelta(days=int(days))).isoformat()
        except Exception as date_err:
            return jsonify({"error": f"Invalid days value: {date_err}"}), 400
    elif custom_date:
        # Validate date format to prevent arbitrary string injection (BUG-C5 fix)
        try:
            from datetime import date as date_cls
            date_cls.fromisoformat(custom_date)
        except (ValueError, TypeError):
            return jsonify({"error": f"Invalid date format: '{custom_date}'. Expected YYYY-MM-DD."}), 400
        remind_date = custom_date
    else:
        return jsonify({"error": "Either days or custom_date is required"}), 400
        
    success = db.schedule_reminder(lead_id, remind_date, user_id=g.user['id'])
    if success:
        return jsonify({
            "success": True, 
            "message": f"Follow-up reminder scheduled for {remind_date}",
            "remind_date": remind_date
        })
    else:
        return jsonify({"error": "Failed to schedule reminder"}), 500


@app.route("/api/reminders", methods=["GET"])
def get_pending_reminders():
    """Get all active pending reminders from the database."""
    reminders = db.get_pending_reminders(user_id=g.user['id'])
    return jsonify({"success": True, "reminders": reminders})


@app.route("/api/leads/<int:lead_id>/dismiss-reminder", methods=["POST"])
def dismiss_lead_reminder(lead_id):
    """Dismiss a pending follow-up reminder for a lead."""
    success = db.dismiss_reminder(lead_id, user_id=g.user['id'])
    if success:
        return jsonify({"success": True, "message": "Reminder dismissed successfully"})
    else:
        return jsonify({"error": "Failed to dismiss reminder"}), 500


# ============================================================
# API Routes — WhatsApp
# ============================================================

@app.route("/api/whatsapp/templates", methods=["GET"])
def get_whatsapp_templates():
    """Get available WhatsApp message templates."""
    templates = WhatsAppMessenger.get_templates()
    return jsonify({"success": True, "templates": templates})


@app.route("/api/whatsapp/generate", methods=["POST"])
def generate_whatsapp_link():
    """
    Generate a WhatsApp link with personalized message.
    
    Request body:
        {
            "phone": "919876543210",
            "template": "website_pitch",
            "custom_message": "",
            "lead": { ... lead data ... }
        }
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
    
    # Create a Lead object from the data
    from collectors.base_collector import Lead
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
    
    # Build message
    message = WhatsAppMessenger.build_message(template_key, lead, custom_message)
    
    # Generate link
    link = WhatsAppMessenger.generate_whatsapp_link(phone, message)
    
    # Save message log if lead has an ID (BUG-M12)
    lead_id = lead_data.get("id")
    if lead_id:
        try:
            db.log_message(lead_id, template_key, message, user_id=g.user['id'])
        except Exception as log_err:
            print(f"Error logging WhatsApp message to DB: {log_err}")
            
    return jsonify({
        "success": True,
        "whatsapp_link": link,
        "message": message
    })


# ============================================================
# API Routes — Export
# ============================================================

@app.route("/api/export/excel", methods=["POST"])
def export_excel():
    """
    Export leads as Excel file (.xlsx) for proper formatting.
    """
    data = request.get_json()
    leads = data.get("leads", [])
    
    if not leads:
        return jsonify({"error": "No leads to export"}), 400
    
    try:
        import pandas as pd
        import io
        
        # Prepare data for DataFrame
        df_data = []
        for lead in leads:
            df_data.append({
                "Business Name": lead.get("name", ""),
                "Phone": lead.get("phone", ""),
                "WhatsApp Number": lead.get("whatsapp_number", ""),
                "Website": lead.get("website", ""),
                "Category": lead.get("category", ""),
                "Address": lead.get("address", ""),
                "City": lead.get("city", ""),
                "Rating": lead.get("rating", ""),
                "Reviews": lead.get("reviews", ""),
                "Priority": lead.get("priority", ""),
                "Instagram": lead.get("instagram", ""),
                "Facebook": lead.get("facebook", ""),
                "Contacted": "Yes" if lead.get("contacted") == 1 or lead.get("contacted") is True else "No",
                "Contact Date": lead.get("contact_date", ""),
                "Notes": lead.get("notes", ""),
                "Custom Pitch": lead.get("custom_pitch", ""),
                "Source": lead.get("source", "google_maps")
            })
            
        df = pd.DataFrame(df_data)
        
        # Write to memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
            
            # Auto-adjust columns width
            from openpyxl.utils import get_column_letter
            worksheet = writer.sheets['Leads']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                # Cap the maximum width to 50 to prevent super wide columns
                max_len = min(max_len, 50)
                worksheet.column_dimensions[get_column_letter(idx + 1)].width = max_len

        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=leads_{timestamp}.xlsx"
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel file: {str(e)}"}), 500


# ============================================================
# API Routes — Configuration
# ============================================================

@app.route("/api/config", methods=["GET"])
def get_config():
    """Check if the server has a default master API key configured."""
    api_key = API_KEY_STORE.get("serpapi", "")
    has_key = bool(api_key)
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else ("***" if api_key else "")
    
    return jsonify({
        "success": True,
        "has_api_key": has_key,
        "masked_key": masked_key
    })


@app.route("/api/config/validate", methods=["POST"])
def validate_config():
    """
    Validate a SerpApi key without storing it on the server.
    This allows secure browser-side storage (localStorage) for deployment.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    api_key = data.get("api_key", "").strip()
    
    if not api_key:
        return jsonify({"error": "API key cannot be empty"}), 400
    
    try:
        import requests as req
        # Test SerpApi Key (use account endpoint to avoid consuming credits)
        test_url = "https://serpapi.com/account"
        params = {"api_key": api_key}
        
        response = req.get(test_url, params=params, timeout=10)
        
        if response.status_code == 401:
            return jsonify({"error": "Invalid SerpApi key"}), 400
            
        return jsonify({"success": True, "message": "API key validated successfully"})
    
    except Exception as e:
        return jsonify({"error": f"Failed to validate API key: {str(e)}"}), 500


@app.route("/api/portfolio/scan", methods=["POST"])
def scan_portfolio():
    """
    Fetch and parse projects from the user's portfolio URL.
    This runs statelessly and lets the browser save the projects.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    portfolio_url = data.get("portfolio_url", "").strip()
    if not portfolio_url:
        return jsonify({"error": "Portfolio URL cannot be empty"}), 400
        
    try:
        projects = PortfolioParser.fetch_and_parse(portfolio_url)
        return jsonify({
            "success": True,
            "portfolio_url": portfolio_url,
            "projects": projects
        })
    except Exception as e:
        return jsonify({"error": f"Failed to scan portfolio: {str(e)}"}), 500


@app.route("/api/outreach/generate-ai", methods=["POST"])
def generate_ai_pitch():
    """
    Generate a unique, highly personalized outreach pitch using Gemini API.
    Runs statelessly - reads key from header X-Gemini-API-Key.
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
    
    if not lead_data:
        return jsonify({"error": "Lead data is required"}), 400
        
    try:
        # Dynamic Mockup Link Construction
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
            min_words=min_words
        )
        
        
        # Save generated pitch persistently in database
        lead_id = lead_data.get("id")
        if lead_id:
            db.update_lead_pitch(lead_id, pitch, user_id=g.user['id'])
            
        return jsonify({
            "success": True,
            "pitch": pitch
        })
    except Exception as e:
        return jsonify({"error": f"AI Generation failed: {str(e)}"}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics."""
    stats = db.get_stats(user_id=g.user['id'])
    return jsonify({"success": True, "stats": stats})


@app.route("/api/history", methods=["GET"])
def get_history():
    """Get search history."""
    history = db.get_search_history(user_id=g.user['id'])
    return jsonify({"success": True, "history": history})


@app.route("/api/leads/<int:lead_id>/scan-socials", methods=["POST"])
def scan_lead_socials(lead_id):
    """
    Scan Google for Instagram and Facebook profiles of a lead on-demand.
    """
    lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
        
    api_key = request.headers.get("X-SerpApi-Key") or API_KEY_STORE.get("serpapi", "")
    if not api_key:
        return jsonify({"error": "SerpApi key not configured"}), 401
        
    instagram_link = ""
    facebook_link = ""
    
    # Combined search for both Instagram and Facebook to save 50% API credits in a single query
    try:
        from serpapi import GoogleSearch
        combined_query = f'(site:instagram.com OR site:facebook.com) "{lead.get("name")}" {lead.get("city")}'
        params = {
            "engine": "google",
            "q": combined_query,
            "api_key": api_key,
            "num": 6 # Fetch top 6 results
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        organic = results.get("organic_results", [])
        for item in organic:
            link = item.get("link", "")
            if "instagram.com/" in link and not instagram_link:
                if not any(x in link for x in ["/p/", "/tags/", "/explore/", "/reel/", "/directory/"]):
                    instagram_link = link
            elif "facebook.com/" in link and not facebook_link:
                if not any(x in link for x in ["/sharer/", "/policies/", "/groups/", "/events/", "/post/"]):
                    facebook_link = link
    except Exception as e:
        print(f"Error scanning combined socials for lead {lead_id}: {e}")
        
    # Update lead in database
    db.update_lead_socials(lead_id, instagram_link, facebook_link, user_id=g.user['id'])
    
    return jsonify({
        "success": True,
        "instagram": instagram_link,
        "facebook": facebook_link
    })


@app.route("/api/config/clear-db", methods=["POST"])
def clear_db():
    """
    Manually clear all uncontacted leads and search history.
    """
    result = db.clear_uncontacted_data(user_id=g.user['id'])
    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify({"error": result.get("error")}), 500


@app.route("/preview/<int:lead_id>")
def live_preview_mockup(lead_id):
    """Serve a stunning personalized website mockup for the business lead."""
    lead = db.get_lead_by_id(lead_id, user_id=g.user['id'] if g.user else None)
    if not lead:
        return "Lead not found", 404
        
    # Fetch sender info from query parameters
    sender_name = request.args.get("sender_name", "")
    sender_brand = request.args.get("sender_brand", "")
    
    # Determine design theme based on category
    category = (lead.get("category") or "").lower()
    name = (lead.get("name") or "").lower()
    
    theme = "default"
    if any(x in category or x in name for x in ["gym", "fitness", "workout", "health", "sports", "trainer", "yoga"]):
        theme = "gym"
    elif any(x in category or x in name for x in ["hotel", "restaurant", "cafe", "food", "dine", "bakery", "sweet", "pizza", "burger", "coffee"]):
        theme = "restaurant"
    elif any(x in category or x in name for x in ["salon", "spa", "beauty", "hair", "parlor", "boutique", "grooming", "clinic", "dental", "doctor", "dentist"]):
        theme = "salon"
        
    return render_template("preview_mockup.html", lead=lead, theme=theme, sender_name=sender_name, sender_brand=sender_brand)


@app.route("/api/leads/<int:lead_id>/scan-email", methods=["POST"])
def scan_lead_email(lead_id):
    """Trigger email scraper with direct website scan and smart SerpApi Google search snippet fallback."""
    lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
        
    website = lead.get("website", "").strip()
    api_key = request.headers.get("X-SerpApi-Key") or API_KEY_STORE.get("serpapi", "")
    
    email = None
    scraped_via = "direct_website"
    
    # 1. First Pass: If website is listed, try free deep crawling
    if website:
        try:
            from utils.email_scraper import EmailScraper
            email = EmailScraper.deep_scrape_business_emails(website)
        except Exception as e:
            print(f"Direct website email scraping failed for {website}: {e}")
            
    # 2. Second Pass: If no email found or no website exists, try SerpApi Fallback Search
    if not email:
        if not api_key:
            # If no API key configured, we cannot proceed with web search fallback
            if not website:
                return jsonify({
                    "success": False,
                    "error": "Lead does not have a website URL listed. Configure your SerpApi Key in Settings to enable Web-Search Fallback."
                }), 400
            else:
                return jsonify({
                    "success": False,
                    "error": "No email found via website scraper. Configure SerpApi Key in Settings to try Web-Search Fallback."
                })
                
        try:
            from serpapi import GoogleSearch
            from utils.email_scraper import EmailScraper
            import re
            
            # Formulate highly focused Google search query for the business's email
            query = f'"{lead.get("name")}" "{lead.get("city")}" email'
            print(f"Running Smart SerpApi Fallback Email Search: {query}...")
            
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": 8  # Top 8 results to maximize search breadth while keeping delay small
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            organic = results.get("organic_results", [])
            
            found_emails = []
            for item in organic:
                # Scan snippet, title, and destination link for any matching emails
                text_to_scan = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('link', '')}"
                matches = re.findall(EmailScraper.EMAIL_REGEX, text_to_scan)
                for m in matches:
                    cleaned = EmailScraper.clean_email(m)
                    if EmailScraper.is_valid_email(cleaned) and cleaned not in found_emails:
                        found_emails.append(cleaned)
            
            if found_emails:
                email = found_emails[0]
                scraped_via = "serpapi_fallback"
                print(f"SerpApi Fallback found email for {lead.get('name')}: {email}")
        except Exception as serp_err:
            print(f"SerpApi Fallback Email search failed: {serp_err}")
            
    if email:
        db.update_lead_email(lead_id, email, user_id=g.user['id'])
        via_msg = "direct website crawling" if scraped_via == "direct_website" else "Google directory fallback search"
        return jsonify({
            "success": True,
            "email": email,
            "message": f"Successfully extracted email via {via_msg}: {email}"
        })
    else:
        msg = "No public email addresses found on website or via web directory searches."
        if not website:
            msg = "No public email addresses listed on online directories for this business."
        return jsonify({
            "success": False,
            "error": msg
        })


@app.route("/api/outreach/generate-email-ai", methods=["POST"])
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
            min_words=min_words
        )
        
        # Parse SUBJECT and BODY
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


@app.route("/api/outreach/send-smtp-email", methods=["POST"])
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
                print(f"STARTTLS failed: {tls_err}")
                
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


# ============================================================
# Run the application
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AI Lead Generation Agent (SerpApi Edition)")
    print("=" * 60)
    print(f"  Dashboard: http://localhost:5000")
    api_status = "Configured" if API_KEY_STORE.get("serpapi") else "Not set (set in dashboard)"
    print(f"  API Key: {api_status}")
    print("=" * 60 + "\n")
    
    app.run(debug=True, port=5000)
