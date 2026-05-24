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
    
    if not query:
        return jsonify({"error": "Please enter a business type/keyword"}), 400
    
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400
    
    # Check API key
    api_key = API_KEY_STORE.get("serpapi", "")
    if not api_key:
        return jsonify({"error": "SerpApi key not configured. Please set it in Settings."}), 401
    
    try:
        # Get already saved place IDs if hide_saved is enabled
        exclude_place_ids = set()
        if hide_saved:
            import sqlite3
            try:
                conn = sqlite3.connect(db.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT place_id FROM leads WHERE place_id IS NOT NULL AND place_id != ''")
                exclude_place_ids = {row[0] for row in cursor.fetchall()}
                conn.close()
            except Exception as db_err:
                print(f"Error fetching saved place IDs: {db_err}")

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
                zone_leads = collector.search(query, f"{zone}, {city}", leads_per_zone, exclude_place_ids)
                all_leads.extend(zone_leads)
        else:
            # Standard single-city search
            all_leads = collector.search(query, city, max_results, exclude_place_ids)
        
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
        
        # Build response
        leads_data = [lead.to_dict() for lead in filtered_leads]
        all_data = [lead.to_dict() for lead in all_leads]
        
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


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    """Delete a lead."""
    db.delete_lead(lead_id)
    return jsonify({"success": True, "message": "Lead deleted"})


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
    """Get current configuration (masked API key)."""
    api_key = API_KEY_STORE.get("serpapi", "")
    has_key = bool(api_key)
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else ("***" if api_key else "")
    
    return jsonify({
        "success": True,
        "has_api_key": has_key,
        "masked_key": masked_key
    })


@app.route("/api/config", methods=["POST"])
def update_config():
    """
    Update configuration (API key).
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
            
        API_KEY_STORE["serpapi"] = api_key
        
        # Also save to .env file for persistence
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        with open(env_path, "w") as f:
            f.write(f"SERPAPI_KEY={api_key}\n")
        
        # Make sure env var is set for the collector
        os.environ["SERPAPI_KEY"] = api_key
        
        return jsonify({"success": True, "message": "API key saved successfully"})
    
    except Exception as e:
        return jsonify({"error": f"Failed to validate API key: {str(e)}"}), 500


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
