import logging
from flask import Blueprint, render_template, request, g, redirect, url_for
from extensions import db
from utils.decorators import admin_required
from psycopg2 import sql

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")

@dashboard_bp.route("/verify-db")
@admin_required
def verify_db():
    """Check database connection and schemas, and render diagnostic dashboard. Admin only."""
    status_info = {}
    conn = None
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
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {};").format(sql.Identifier(table)))
                count = cursor.fetchone()[0]
                table_statuses[table] = {
                    "exists": True,
                    "status": "HEALTHY",
                    "rows": count
                }
            except Exception as tbl_err:
                conn.rollback()
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
                cursor.execute("SELECT id, username, email, phone, created_at FROM users ORDER BY created_at DESC;")
                for row in cursor.fetchall():
                    user_dict = dict(row)
                    if user_dict.get("created_at"):
                        user_dict["created_at_str"] = user_dict["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        user_dict["created_at_str"] = "N/A"
                    users_list.append(user_dict)
            except Exception as users_err:
                conn.rollback()
                logger.error(f"Error fetching users list: {users_err}")
        status_info["users_list"] = users_list
        
        status_info["error"] = None
    except Exception as e:
        status_info["connection"] = "FAILED"
        status_info["error"] = str(e)
        status_info["tables"] = {}
        status_info["version"] = "N/A"
        status_info["users_list"] = []
    finally:
        if conn:
            db._release_connection(conn)
        
    return render_template("db_status.html", status=status_info)

@dashboard_bp.route("/preview/<int:lead_id>")
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

@dashboard_bp.route("/terms")
def terms():
    """Serve Terms of Service page."""
    return render_template("terms.html")

@dashboard_bp.route("/privacy")
def privacy():
    """Serve Privacy Policy page."""
    return render_template("privacy.html")

@dashboard_bp.route("/admin")
@admin_required
def admin_dashboard():
    """Serve Admin user management and server statistics dashboard."""
    status_info = {}
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Total counts
        cursor.execute("SELECT COUNT(*) FROM users;")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE;")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads;")
        total_leads = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM search_history;")
        total_searches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM message_log;")
        total_logs = cursor.fetchone()[0]
        
        status_info["stats"] = {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "total_leads": total_leads,
            "total_searches": total_searches,
            "total_logs": total_logs
        }
        
        # Users list with pagination
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1
        per_page = 10
        offset = (page - 1) * per_page
        
        cursor.execute("SELECT id, username, email, phone, created_at, is_admin, is_active FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s;", (per_page, offset))
        users_list = []
        for row in cursor.fetchall():
            u = dict(row)
            if u["created_at"]:
                u["created_at_str"] = u["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            else:
                u["created_at_str"] = "N/A"
            users_list.append(u)
        status_info["users"] = users_list
        
        total_pages = (total_users + per_page - 1) // per_page if total_users > 0 else 1
        status_info["pagination"] = {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_users": total_users,
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
        
        # System Configuration info
        master_key = db.get_system_setting("serpapi_key")
        using_env = False
        if not master_key:
            import os
            master_key = os.getenv("SERPAPI_KEY", "")
            using_env = bool(master_key)
            
        status_info["master_serpapi_key_configured"] = bool(master_key)
        status_info["master_serpapi_key_masked"] = f"{master_key[:8]}...{master_key[-4:]}" if master_key and len(master_key) > 12 else ("***" if master_key else "")
        status_info["master_serpapi_key_source"] = "Environment Variable" if using_env else ("Database" if master_key else "Not Configured")
        
        db._release_connection(conn)
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        status_info["stats"] = {
            "total_users": 0, "active_users": 0, "inactive_users": 0,
            "total_leads": 0, "total_searches": 0, "total_logs": 0
        }
        status_info["users"] = []
        
    return render_template("admin.html", status=status_info)

@dashboard_bp.route("/audit/<int:lead_id>")
def audit_report_page(lead_id):
    """Serve the public dynamic SEO/Performance Audit Report page for a business lead."""
    # Note: We do NOT enforce login or user_id mapping so that the link is publicly shareable with the client!
    lead = db.get_lead_by_id(lead_id)
    if not lead:
        return "Audit report not found", 404
        
    audit_data_str = lead.get("audit_data", "")
    audit = {}
    if audit_data_str:
        try:
            import json
            audit = json.loads(audit_data_str)
        except Exception as e:
            logger.error(f"Error parsing audit data for lead {lead_id}: {e}")
            
    return render_template("audit_report.html", lead=lead, audit=audit)
