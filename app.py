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
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response, send_file
from flask_cors import CORS
from dotenv import load_dotenv

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

# Initialize database
db = Database()

# Store API key in memory (loaded from .env or set via API)
API_KEY_STORE = {
    "serpapi": os.getenv("SERPAPI_KEY", "")
}


# ============================================================
# Page Routes
# ============================================================

@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


# ============================================================
# API Routes — Search & Leads
# ============================================================

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
            try:
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT place_id FROM leads WHERE place_id IS NOT NULL AND place_id != ''")
                exclude_place_ids = {row[0] for row in cursor.fetchall()}
            except Exception as db_err:
                print(f"Error fetching saved place IDs: {db_err}")
            finally:
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
                # Search using zone name combined with city
                zone_leads = collector.search(query, f"{zone}, {city}", leads_per_zone, exclude_place_ids, start_offset, api_key=api_key)
                all_leads.extend(zone_leads)
        else:
            # Standard single-city search
            all_leads = collector.search(query, city, max_results, exclude_place_ids, start_offset, api_key=api_key)
        
        # Clean the data (standardize, assign priority, and DEDUPLICATE combined leads)
        all_leads = DataCleaner.clean_leads(all_leads)
        
        # Filter out businesses with websites (unless requested)
        filtered_leads = DataCleaner.filter_leads(all_leads, include_with_website)
        
        # Cap to max_results to match the requested amount
        filtered_leads = filtered_leads[:max_results]
        all_leads = all_leads[:max_results]
        
        # Save to database
        db.save_leads(all_leads)
        
        search_query_log = f"{query} (Deep Scan)" if deep_scan else query
        db.save_search(search_query_log, city, len(all_leads), len(filtered_leads))
        
        # Fetch the saved leads from DB to get database IDs and social links
        db_leads_dict = {}
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            place_ids = [l.place_id for l in all_leads if l.place_id]
            if place_ids:
                placeholders = ",".join("?" for _ in place_ids)
                cursor.execute(f"SELECT * FROM leads WHERE place_id IN ({placeholders})", place_ids)
                db_leads_dict = {row['place_id']: dict(row) for row in cursor.fetchall()}
        except Exception as db_err:
            print(f"Error fetching database IDs for search response: {db_err}")
        finally:
            conn.close()

        # Build response
        leads_data = []
        for lead in filtered_leads:
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
            leads_data.append(lead_dict)

        all_data = []
        for lead in all_leads:
            lead_dict = lead.to_dict()
            db_lead = db_leads_dict.get(lead.place_id)
            if db_lead:
                lead_dict['id'] = db_lead['id']
                lead_dict['instagram'] = db_lead.get('instagram') or ''
                lead_dict['facebook'] = db_lead.get('facebook') or ''
                lead_dict['custom_pitch'] = db_lead.get('custom_pitch') or ''
                if not lead_dict.get('is_broken_website'):
                    lead_dict['is_broken_website'] = db_lead.get('is_broken_website', 0) or 0
                if not lead_dict.get('line_type'):
                    lead_dict['line_type'] = db_lead.get('line_type') or ''
            else:
                lead_dict['id'] = None
                lead_dict['instagram'] = ''
                lead_dict['facebook'] = ''
                lead_dict['custom_pitch'] = ''
            all_data.append(lead_dict)
        
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
    
    leads = db.get_all_leads(priority_filter=priority, city_filter=city)
    return jsonify({"success": True, "leads": leads})


@app.route("/api/leads/<int:lead_id>/contact", methods=["POST"])
def mark_lead_contacted(lead_id):
    """Mark a lead as contacted."""
    data = request.get_json() or {}
    notes = data.get("notes", "")
    
    db.mark_contacted(lead_id, notes)
    return jsonify({"success": True, "message": "Lead marked as contacted"})


@app.route("/api/leads/<int:lead_id>/pipeline", methods=["POST"])
def update_lead_pipeline(lead_id):
    """Update lead pipeline stage."""
    data = request.get_json() or {}
    stage = data.get("stage", "NEW").upper()
    
    if stage not in ["NEW", "PITCHED", "INTERESTED", "CONVERTED", "IGNORED"]:
        return jsonify({"error": "Invalid pipeline stage"}), 400
        
    success = db.update_lead_pipeline_stage(lead_id, stage)
    if success:
        return jsonify({"success": True, "message": f"Lead pipeline updated to {stage}", "stage": stage})
    else:
        return jsonify({"error": "Failed to update pipeline stage"}), 500


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    """Delete a lead."""
    db.delete_lead(lead_id)
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
        remind_date = custom_date
    else:
        return jsonify({"error": "Either days or custom_date is required"}), 400
        
    success = db.schedule_reminder(lead_id, remind_date)
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
    reminders = db.get_pending_reminders()
    return jsonify({"success": True, "reminders": reminders})


@app.route("/api/leads/<int:lead_id>/dismiss-reminder", methods=["POST"])
def dismiss_lead_reminder(lead_id):
    """Dismiss a pending follow-up reminder for a lead."""
    success = db.dismiss_reminder(lead_id)
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
        # Test SerpApi Key
        test_url = "https://serpapi.com/search"
        params = {"engine": "google", "q": "test", "api_key": api_key}
        
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
    sender = data.get("sender", {})
    refine_feedback = data.get("refine_feedback")
    previous_pitch = data.get("previous_pitch")
    custom_pitch_rules = data.get("custom_pitch_rules", "")
    
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
            sender_info=sender,
            refine_feedback=refine_feedback,
            previous_pitch=previous_pitch,
            mockup_link=mockup_link,
            custom_pitch_rules=custom_pitch_rules
        )
        
        
        # Save generated pitch persistently in database
        lead_id = lead_data.get("id")
        if lead_id:
            db.update_lead_pitch(lead_id, pitch)
            
        return jsonify({
            "success": True,
            "pitch": pitch
        })
    except Exception as e:
        return jsonify({"error": f"AI Generation failed: {str(e)}"}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics."""
    stats = db.get_stats()
    return jsonify({"success": True, "stats": stats})


@app.route("/api/history", methods=["GET"])
def get_history():
    """Get search history."""
    history = db.get_search_history()
    return jsonify({"success": True, "history": history})


@app.route("/api/leads/<int:lead_id>/scan-socials", methods=["POST"])
def scan_lead_socials(lead_id):
    """
    Scan Google for Instagram and Facebook profiles of a lead on-demand.
    """
    lead = db.get_lead_by_id(lead_id)
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
    db.update_lead_socials(lead_id, instagram_link, facebook_link)
    
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
    result = db.clear_uncontacted_data()
    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify({"error": result.get("error")}), 500


@app.route("/preview/<int:lead_id>")
def live_preview_mockup(lead_id):
    """Serve a stunning personalized website mockup for the business lead."""
    lead = db.get_lead_by_id(lead_id)
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
    """Trigger email scraper for a lead website on demand."""
    lead = db.get_lead_by_id(lead_id)
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
        
    website = lead.get("website", "").strip()
    if not website:
        return jsonify({"error": "Lead does not have a website URL listed."}), 400
        
    try:
        from utils.email_scraper import EmailScraper
        email = EmailScraper.deep_scrape_business_emails(website)
        
        if email:
            db.update_lead_email(lead_id, email)
            return jsonify({
                "success": True,
                "email": email,
                "message": f"Successfully extracted email: {email}"
            })
        else:
            return jsonify({
                "success": False,
                "message": "No public email addresses found on website."
            })
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500


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
    sender = data.get("sender", {})
    custom_pitch_rules = data.get("custom_pitch_rules", "")
    
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
            sender_info=sender,
            mockup_link=mockup_link,
            custom_pitch_rules=custom_pitch_rules
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
        
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
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
            db.update_lead_pipeline_stage(lead_id, "PITCHED")
            
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
