import logging
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, g, session
from extensions import db
from utils.portfolio import PortfolioParser
from utils.decorators import admin_required

logger = logging.getLogger(__name__)
config_bp = Blueprint('api_config', __name__)

from extensions import API_KEY_STORE

@config_bp.route("/export/excel", methods=["POST"])
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

@config_bp.route("/encryption-key", methods=["GET"])
def get_encryption_key():
    """
    Get a secure, session-bound random key for the frontend to encrypt/decrypt values in localStorage.
    Only authenticated users can fetch this.
    """
    if 'local_storage_key' not in session:
        import secrets
        session['local_storage_key'] = secrets.token_hex(32)
    return jsonify({"key": session['local_storage_key']})

@config_bp.route("/config", methods=["GET"])
def get_config():
    """Check if the server has a default master API key configured."""
    api_key = db.get_system_setting("serpapi_key")
    if not api_key:
        api_key = API_KEY_STORE.get("serpapi", "")
        
    has_key = bool(api_key)
    is_admin = g.user and g.user.get('is_admin')
    
    if is_admin:
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else ("***" if api_key else "")
    else:
        masked_key = ""
    
    return jsonify({
        "success": True,
        "has_api_key": has_key,
        "masked_key": masked_key
    })

@config_bp.route("/admin/config/serpapi", methods=["POST"])
@admin_required
def update_admin_serpapi_key():
    """Update system-wide master SerpApi Key. Admin only."""
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    
    # Validate the key if one is provided
    if api_key:
        try:
            import requests as req
            test_url = "https://serpapi.com/account"
            params = {"api_key": api_key}
            response = req.get(test_url, params=params, timeout=10)
            if response.status_code == 401:
                return jsonify({"error": "Invalid SerpApi key"}), 400
        except Exception as e:
            return jsonify({"error": f"Failed to validate API key: {str(e)}"}), 500
            
    success = db.save_system_setting("serpapi_key", api_key)
    if success:
        return jsonify({"success": True, "message": "Master SerpApi key updated successfully"})
    else:
        return jsonify({"error": "Failed to update master SerpApi key in database"}), 500

@config_bp.route("/config/validate", methods=["POST"])
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
        test_url = "https://serpapi.com/account"
        params = {"api_key": api_key}
        
        response = req.get(test_url, params=params, timeout=10)
        if response.status_code == 401:
            return jsonify({"error": "Invalid SerpApi key"}), 400
            
        return jsonify({"success": True, "message": "API key validated successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to validate API key: {str(e)}"}), 500

@config_bp.route("/portfolio/scan", methods=["POST"])
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

@config_bp.route("/config/clear-db", methods=["POST"])
def clear_db():
    """
    Manually clear all uncontacted leads and search history.
    """
    result = db.clear_uncontacted_data(user_id=g.user['id'])
    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify({"error": result.get("error")}), 500

@config_bp.route("/config/delete-account", methods=["DELETE"])
def delete_account():
    """Delete account and all user data permanently."""
    user_id = g.user['id']
    success = db.delete_user_account(user_id)
    if success:
        session.clear()
        return jsonify({"success": True, "message": "Account deleted permanently"})
    else:
        return jsonify({"error": "Failed to delete account"}), 500

@config_bp.route("/config/export-data", methods=["GET"])
def export_data():
    """Export all user records for GDPR portability compliance."""
    user_id = g.user['id']
    conn = db._get_connection()
    cursor = conn.cursor()
    try:
        # User details
        cursor.execute("SELECT id, username, email, phone, created_at, is_admin FROM users WHERE id = %s", (user_id,))
        user_row = cursor.fetchone()
        user_data = dict(user_row) if user_row else {}
        
        # Leads
        cursor.execute("SELECT * FROM leads WHERE user_id = %s", (user_id,))
        leads = [dict(row) for row in cursor.fetchall()]
        
        # Search history
        cursor.execute("SELECT * FROM search_history WHERE user_id = %s", (user_id,))
        searches = [dict(row) for row in cursor.fetchall()]
        
        # Message log
        cursor.execute("SELECT * FROM message_log WHERE user_id = %s", (user_id,))
        logs = [dict(row) for row in cursor.fetchall()]
        
        export_payload = {
            "exported_at": datetime.now().isoformat(),
            "user": user_data,
            "leads": leads,
            "search_history": searches,
            "message_log": logs
        }
        
        import json
        from datetime import date
        from decimal import Decimal
        
        class SafeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, (datetime, date)):
                    return o.isoformat()
                if isinstance(o, Decimal):
                    return float(o)
                return super().default(o)
                
        json_data = json.dumps(export_payload, cls=SafeEncoder, indent=2)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return Response(
            json_data,
            mimetype="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=leadhunter_data_export_{timestamp}.json"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        return jsonify({"error": f"Failed to export data: {str(e)}"}), 500
    finally:
        db._release_connection(conn)

@config_bp.route("/admin/users/<int:target_user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_user_active(target_user_id):
    """Toggle is_active flag for a user. Admin only."""
    if target_user_id == g.user['id']:
        return jsonify({"error": "You cannot deactivate your own account"}), 400
        
    data = request.get_json() or {}
    status = data.get("active")
    if status is None:
        return jsonify({"error": "Missing 'active' parameter"}), 400
        
    success = db.toggle_user_active(target_user_id, bool(status))
    if success:
        return jsonify({"success": True, "message": f"User active status updated to {status}"})
    else:
        return jsonify({"error": "Failed to update user active status"}), 500

@config_bp.route("/admin/users/<int:target_user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_user_admin(target_user_id):
    """Toggle is_admin flag for a user. Admin only."""
    if target_user_id == g.user['id']:
        return jsonify({"error": "You cannot modify your own admin privileges"}), 400
        
    data = request.get_json() or {}
    status = data.get("admin")
    if status is None:
        return jsonify({"error": "Missing 'admin' parameter"}), 400
        
    success = db.toggle_user_admin(target_user_id, bool(status))
    if success:
        return jsonify({"success": True, "message": f"User admin status updated to {status}"})
    else:
        return jsonify({"error": "Failed to update user admin status"}), 500

@config_bp.route("/config/drips", methods=["GET", "POST"])
def manage_drip_config():
    """Save or retrieve drip follow-ups configuration for the user."""
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == "POST":
        data = request.get_json() or {}
        delay_days = data.get("delay_days", 3)
        max_followups = data.get("max_followups", 2)
        followup_subject = data.get("followup_subject", "Quick follow up regarding proposal").strip()
        followup_template = data.get("followup_template", "").strip()
        is_enabled = data.get("is_enabled", False)
        
        try:
            delay_days = int(delay_days)
            max_followups = int(max_followups)
        except ValueError:
            return jsonify({"error": "Invalid delay days or max follow-ups format"}), 400
            
        success = db.save_drip_config(user_id, delay_days, max_followups, followup_subject, followup_template, bool(is_enabled))
        if success:
            return jsonify({"success": True, "message": "Drip campaign configurations saved successfully."})
        return jsonify({"error": "Failed to save Drip configuration."}), 500
    else:
        # GET request
        config = db.get_drip_config(user_id)
        if not config:
            return jsonify({
                "configured": False,
                "delay_days": 3,
                "max_followups": 2,
                "followup_subject": "Quick follow up regarding proposal",
                "followup_template": "",
                "is_enabled": False
            })
        config["configured"] = True
        return jsonify(config)
