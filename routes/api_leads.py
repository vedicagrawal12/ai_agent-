import logging
import re
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, g
from extensions import db, limiter, collector, cache
from utils.data_cleaner import DataCleaner
from utils.task_runner import TaskRunner

logger = logging.getLogger(__name__)
leads_bp = Blueprint('api_leads', __name__)

# To share API keys, we import from extensions
from extensions import API_KEY_STORE

def get_resolved_serpapi_key():
    """Resolve the active SerpApi key from Database, fallback to Env, then request headers."""
    db_key = db.get_system_setting("serpapi_key")
    if db_key:
        return db_key
    env_key = API_KEY_STORE.get("serpapi", "")
    if env_key:
        return env_key
    return request.headers.get("X-SerpApi-Key", "")

def enrich_lead_dict(lead, db_leads_dict):
    lead_dict = lead.to_dict()
    db_lead = db_leads_dict.get(lead.place_id)
    if db_lead:
        lead_dict['id'] = db_lead['id']
        lead_dict['instagram'] = db_lead.get('instagram') or ''
        lead_dict['facebook'] = db_lead.get('facebook') or ''
        lead_dict['custom_pitch'] = db_lead.get('custom_pitch') or ''
        # Prefer in-memory values for freshly-scanned fields, fall back to DB
        lead_dict['is_broken_website'] = bool(lead_dict.get('is_broken_website') or db_lead.get('is_broken_website', False))
        if not lead_dict.get('line_type'):
            lead_dict['line_type'] = db_lead.get('line_type') or ''
    else:
        lead_dict['id'] = None
        lead_dict['instagram'] = ''
        lead_dict['facebook'] = ''
        lead_dict['custom_pitch'] = ''
        lead_dict['is_broken_website'] = bool(lead_dict.get('is_broken_website', False))
    return lead_dict

def run_background_search(user_id, query, city, max_results, include_with_website, hide_saved, deep_scan, zones, start_offset, api_key):
    # Get already saved place IDs if hide_saved is enabled
    exclude_place_ids = set()
    if hide_saved:
        conn = None
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT place_id FROM leads WHERE user_id = %s AND place_id IS NOT NULL AND place_id != ''", (user_id,))
            exclude_place_ids = {row[0] for row in cursor.fetchall()}
        except Exception as db_err:
            logger.error(f"Error fetching saved place IDs: {db_err}")
        finally:
            if conn:
                db._release_connection(conn)

    # Search for businesses
    all_leads = []
    if deep_scan and zones:
        leads_per_zone = max(10, max_results // len(zones))
        for zone in zones:
            zone = zone.strip()
            if not zone:
                continue
            zone_leads = collector.search(query, f"{zone}, {city}", leads_per_zone, exclude_place_ids, 0, api_key=api_key)
            all_leads.extend(zone_leads)
            for zl in zone_leads:
                if zl.place_id:
                    exclude_place_ids.add(zl.place_id)
    else:
        all_leads = collector.search(query, city, max_results, exclude_place_ids, start_offset, api_key=api_key)
    
    # Clean and filter leads
    all_leads = DataCleaner.clean_leads(all_leads)
    filtered_leads = DataCleaner.filter_leads(all_leads, include_with_website)
    
    # Save all discovered leads to database
    db.save_leads(all_leads, user_id=user_id)
    
    filtered_leads = filtered_leads[:max_results]
    all_leads = all_leads[:max_results]
    
    db.save_search(
        query=query,
        city=city,
        results_count=len(all_leads),
        leads_count=len(filtered_leads),
        user_id=user_id,
        deep_scan=deep_scan,
        zones=zones,
        include_with_website=include_with_website,
        hide_saved=hide_saved
    )
    
    # Fetch the saved leads from DB to get database IDs and social links
    db_leads_dict = {}
    conn = None
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        place_ids = [l.place_id for l in all_leads if l.place_id]
        if place_ids:
            placeholders = ",".join("%s" for _ in place_ids)
            cursor.execute(f"SELECT * FROM leads WHERE user_id = %s AND place_id IN ({placeholders})", [user_id] + place_ids)
            db_leads_dict = {row['place_id']: dict(row) for row in cursor.fetchall()}
    except Exception as db_err:
        logger.error(f"Error fetching database IDs for search response: {db_err}")
    finally:
        if conn:
            db._release_connection(conn)

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
        "broken_websites": sum(1 for l in filtered_leads if l.is_broken_website),
    }
    
    return {
        "leads": leads_data,
        "all_results": all_data,
        "stats": stats,
        "query": f"{query} in {city}"
    }

@leads_bp.route("/search", methods=["POST"])
@limiter.limit("10 per minute")
def search_businesses():
    """
    Search Google Maps for businesses asynchronously.
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
        cleaned_zones = []
        for z in zones[:10]:
            if isinstance(z, str):
                z_clean = z.strip()[:50]
                z_clean = re.sub(r'[^a-zA-Z0-9\s\-\.]', '', z_clean)
                z_clean = ' '.join(z_clean.split())
                if z_clean:
                    cleaned_zones.append(z_clean)
        zones = cleaned_zones
    else:
        zones = []
    start_offset = data.get("start_offset", 0)
    
    if not query:
        return jsonify({"error": "Please enter a business type/keyword"}), 400
    
    if not city:
        return jsonify({"error": "Please enter a city name"}), 400
    
    # Check API key
    api_key = get_resolved_serpapi_key()
    if not api_key:
        if g.user and g.user.get('is_admin'):
            return jsonify({"error": "SerpApi key not configured. Please configure the master key in the Admin Console."}), 401
        else:
            return jsonify({"error": "Server busy or under maintenance... take a while, have a teacup and come back."}), 401
    
    try:
        task_id = TaskRunner.submit(
            run_background_search,
            user_id=g.user['id'],
            query=query,
            city=city,
            max_results=max_results,
            include_with_website=include_with_website,
            hide_saved=hide_saved,
            deep_scan=deep_scan,
            zones=zones,
            start_offset=start_offset,
            api_key=api_key
        )
        return jsonify({"success": True, "task_id": task_id})
    except Exception as e:
        logger.error(f"Search submission error: {e}")
        return jsonify({"error": str(e)}), 500

@leads_bp.route("/search/status/<task_id>", methods=["GET"])
def get_search_status(task_id):
    """
    Check status of an asynchronous search task.
    """
    status_info = TaskRunner.get_status(task_id)
    return jsonify(status_info)

@leads_bp.route("/leads", methods=["GET"])
def get_saved_leads():
    """Get all saved leads from the database with optional pagination."""
    priority = request.args.get("priority")
    city = request.args.get("city")
    page_val = request.args.get("page")
    per_page_val = request.args.get("per_page")
    
    if page_val is not None or per_page_val is not None:
        try:
            page = int(page_val) if page_val else 1
            per_page = int(per_page_val) if per_page_val else 50
        except ValueError:
            return jsonify({"error": "Invalid page or per_page query parameters"}), 400
            
        result = db.get_all_leads_paginated(
            priority_filter=priority,
            city_filter=city,
            user_id=g.user['id'],
            page=page,
            per_page=per_page
        )
        return jsonify({
            "success": True,
            "leads": result["leads"],
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "pages": result["pages"]
        })
    else:
        leads = db.get_all_leads(priority_filter=priority, city_filter=city, user_id=g.user['id'])
        return jsonify({"success": True, "leads": leads})

@leads_bp.route("/leads/<int:lead_id>/contact", methods=["POST"])
def mark_lead_contacted(lead_id):
    """Mark a lead as contacted."""
    data = request.get_json() or {}
    notes = data.get("notes", "")
    db.mark_contacted(lead_id, notes, user_id=g.user['id'])
    return jsonify({"success": True, "message": "Lead marked as contacted"})

@leads_bp.route("/leads/<int:lead_id>/pipeline", methods=["POST"])
def update_lead_pipeline(lead_id):
    """Update lead pipeline stage."""
    data = request.get_json() or {}
    stage = data.get("stage", "NEW").upper()
    
    if stage not in ["NEW", "PITCHED", "INTERESTED", "REPLIED", "CONVERTED", "CLOSED", "IGNORED"]:
        return jsonify({"error": "Invalid pipeline stage"}), 400
        
    success = db.update_lead_pipeline_stage(lead_id, stage, user_id=g.user['id'])
    if success:
        return jsonify({"success": True, "message": f"Lead pipeline updated to {stage}", "stage": stage})
    else:
        return jsonify({"error": "Failed to update pipeline stage"}), 500

@leads_bp.route("/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    """Delete a lead."""
    db.delete_lead(lead_id, user_id=g.user['id'])
    return jsonify({"success": True, "message": "Lead deleted"})

@leads_bp.route("/leads/<int:lead_id>/schedule-reminder", methods=["POST"])
def schedule_lead_reminder(lead_id):
    """Schedule a follow-up reminder for a lead."""
    data = request.get_json() or {}
    days = data.get("days")
    custom_date = data.get("custom_date")
    
    if days is not None:
        try:
            remind_date = (date.today() + timedelta(days=int(days))).isoformat()
        except Exception as date_err:
            return jsonify({"error": f"Invalid days value: {date_err}"}), 400
    elif custom_date:
        try:
            date.fromisoformat(custom_date)
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

@leads_bp.route("/reminders", methods=["GET"])
def get_pending_reminders():
    """Get all active pending reminders from the database."""
    reminders = db.get_pending_reminders(user_id=g.user['id'])
    return jsonify({"success": True, "reminders": reminders})

@leads_bp.route("/leads/<int:lead_id>/dismiss-reminder", methods=["POST"])
def dismiss_lead_reminder(lead_id):
    """Dismiss a pending follow-up reminder for a lead."""
    success = db.dismiss_reminder(lead_id, user_id=g.user['id'])
    if success:
        return jsonify({"success": True, "message": "Reminder dismissed successfully"})
    else:
        return jsonify({"error": "Failed to dismiss reminder"}), 500

def make_stats_cache_key():
    return f"stats_user_{g.user['id']}" if g.user else "stats_user_none"

@leads_bp.route("/stats", methods=["GET"])
@cache.cached(timeout=60, key_prefix=make_stats_cache_key)
def get_stats():
    """Get dashboard statistics."""
    stats = db.get_stats(user_id=g.user['id'])
    return jsonify({"success": True, "stats": stats})

@leads_bp.route("/history", methods=["GET"])
def get_history():
    """Get search history."""
    history = db.get_search_history(user_id=g.user['id'])
    return jsonify({"success": True, "history": history})

@leads_bp.route("/leads/<int:lead_id>/scan-socials", methods=["POST"])
@limiter.limit("10 per minute")
def scan_lead_socials(lead_id):
    """Scan Google for Instagram and Facebook profiles of a lead on-demand."""
    lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
        
    api_key = get_resolved_serpapi_key()
    if not api_key:
        if g.user and g.user.get('is_admin'):
            return jsonify({"error": "SerpApi key not configured. Please configure the master key in the Admin Console."}), 401
        else:
            return jsonify({"error": "Server busy or under maintenance... take a while, have a teacup and come back."}), 401
        
    instagram_link = ""
    facebook_link = ""
    
    try:
        from serpapi import GoogleSearch
        combined_query = f'(site:instagram.com OR site:facebook.com) "{lead.get("name")}" {lead.get("city")}'
        params = {
            "engine": "google",
            "q": combined_query,
            "api_key": api_key,
            "num": 6
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
        logger.error(f"Error scanning combined socials for lead {lead_id}: {e}")
        
    db.update_lead_socials(lead_id, instagram_link, facebook_link, user_id=g.user['id'])
    
    return jsonify({
        "success": True,
        "instagram": instagram_link,
        "facebook": facebook_link
    })

@leads_bp.route("/leads/<int:lead_id>/scan-email", methods=["POST"])
@limiter.limit("10 per minute")
def scan_lead_email(lead_id):
    """Trigger email scraper with direct website scan and smart SerpApi search snippet fallback."""
    lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
        
    website = lead.get("website", "").strip()
    api_key = get_resolved_serpapi_key()
    
    email = None
    scraped_via = "direct_website"
    
    if website:
        try:
            from utils.email_scraper import EmailScraper
            email = EmailScraper.deep_scrape_business_emails(website)
        except Exception as e:
            logger.error(f"Direct website email scraping failed for {website}: {e}")
            
    if not email:
        if not api_key:
            if not website:
                if g.user and g.user.get('is_admin'):
                    err = "Lead does not have a website URL listed. Please configure your master SerpApi Key in the Admin Console to enable Web-Search Fallback."
                else:
                    err = "Server busy or under maintenance... take a while, have a teacup and come back."
                return jsonify({
                    "success": False,
                    "error": err
                }), 400
            else:
                if g.user and g.user.get('is_admin'):
                    err = "No email found via website scraper. Please configure your master SerpApi Key in the Admin Console to try Web-Search Fallback."
                else:
                    err = "Server busy or under maintenance... take a while, have a teacup and come back."
                return jsonify({
                    "success": False,
                    "error": err
                })
                
        try:
            from serpapi import GoogleSearch
            from utils.email_scraper import EmailScraper
            
            query = f'"{lead.get("name")}" "{lead.get("city")}" email'
            logger.info(f"Running Smart SerpApi Fallback Email Search: {query}...")
            
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": 8
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            organic = results.get("organic_results", [])
            
            found_emails = []
            for item in organic:
                text_to_scan = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('link', '')}"
                matches = re.findall(EmailScraper.EMAIL_REGEX, text_to_scan)
                for m in matches:
                    cleaned = EmailScraper.clean_email(m)
                    if EmailScraper.is_valid_email(cleaned) and cleaned not in found_emails:
                        found_emails.append(cleaned)
            
            if found_emails:
                email = found_emails[0]
                scraped_via = "serpapi_fallback"
                logger.info(f"SerpApi Fallback found email for {lead.get('name')}: {email}")
        except Exception as serp_err:
            logger.error(f"SerpApi Fallback Email search failed: {serp_err}")
            
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

@leads_bp.route("/leads/import", methods=["POST"])
def import_leads():
    """Import leads from CSV file upload."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded under key 'file'"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are allowed"}), 400
        
    try:
        import csv
        import io
        from collectors.base_collector import Lead
        from utils.email_scraper import EmailScraper
        
        # Read the file text
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        reader = csv.DictReader(stream)
        
        # Lowercase headers to make mapping case-insensitive
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames] if reader.fieldnames else []
        
        # Required columns: name
        if 'name' not in reader.fieldnames:
            return jsonify({"error": "CSV must contain a 'name' column"}), 400
            
        leads_to_save = []
        for row in reader:
            name = row.get('name', '').strip()
            if not name:
                continue
                
            phone = row.get('phone', '').strip()
            # Clean/standardize phone using DataCleaner
            if phone:
                phone = DataCleaner.standardize_phone(phone)
                
            email = row.get('email', '').strip()
            if email:
                email = EmailScraper.clean_email(email)
                if not EmailScraper.is_valid_email(email):
                    email = ''
                    
            website = row.get('website', '').strip()
            address = row.get('address', '').strip()
            city = row.get('city', '').strip() or 'Unknown'
            
            # Priority validation
            priority = row.get('priority', 'LOW').strip().upper()
            if priority not in ["HIGH", "MEDIUM", "LOW", "IGNORE"]:
                priority = "LOW"
                
            place_id = row.get('place_id', '').strip()
            if not place_id:
                import hashlib
                hash_input = f"{name.lower().strip()}_{city.lower().strip()}_{phone.strip()}"
                hasher = hashlib.md5(hash_input.encode('utf-8'))
                place_id = f"imported_{hasher.hexdigest()[:16]}"
                
            lead_obj = Lead(
                name=name,
                phone=phone,
                website=website,
                address=address,
                city=city,
                place_id=place_id,
                priority=priority,
                email=email
            )
            leads_to_save.append(lead_obj)
            
        if not leads_to_save:
            return jsonify({"success": True, "message": "No valid leads found in CSV", "imported_count": 0})
            
        new_leads_saved = db.save_leads(leads_to_save, user_id=g.user['id'])
        
        return jsonify({
            "success": True,
            "message": f"Successfully processed {len(leads_to_save)} leads, saved {new_leads_saved} new records.",
            "imported_count": len(leads_to_save),
            "new_saved": new_leads_saved
        })
    except Exception as e:
        logger.error(f"Error importing CSV leads: {e}")
        return jsonify({"error": f"Failed to parse CSV file: {str(e)}"}), 500

@leads_bp.route("/leads/<int:lead_id>/audit", methods=["POST"])
@limiter.limit("5 per minute")
def audit_lead_website(lead_id):
    """Run an on-demand SEO and Speed audit on the lead's website."""
    lead = db.get_lead_by_id(lead_id, user_id=g.user['id'])
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
        
    website = lead.get("website", "").strip()
    if not website:
        return jsonify({"error": "Lead does not have a website URL listed."}), 400
        
    try:
        from utils.website_auditor import audit_website
        import json
        
        logger.info(f"Auditing website for lead {lead_id} ({lead.get('name')}): {website}")
        audit_results = audit_website(website)
        
        if not audit_results:
            return jsonify({"error": "Failed to scan website. Please verify the link is active."}), 400
            
        audit_data_str = json.dumps(audit_results)
        db.update_lead_audit_data(lead_id, audit_data_str, user_id=g.user['id'])
        
        return jsonify({
            "success": True,
            "message": "SEO and Performance Audit completed successfully!",
            "audit_data": audit_results
        })
    except Exception as e:
        logger.error(f"Error auditing website for lead {lead_id}: {e}", exc_info=True)
        return jsonify({"error": f"Audit execution failed: {str(e)}"}), 500

@leads_bp.route("/stats/analytics", methods=["GET"])
def get_analytics_stats():
    """Fetch aggregated conversion analytics, daily timeline, and telemetry ratios."""
    user_id = g.user['id'] if (g.get('user') and 'id' in g.user) else None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    conn = db._get_connection()
    cursor = conn.cursor()
    try:
        # 1. Funnel Stages Metrics
        # Scouted (total leads), Pitched (contacted = True), Opened (opened = True in logs),
        # Clicked (clicked = True in logs or pipeline stage >= INTERESTED),
        # Replied (is_reply = True in logs or pipeline stage = REPLIED),
        # Closed (pipeline stage = CLOSED)
        cursor.execute("""
            SELECT 
                COUNT(l.id) as scouted,
                COUNT(CASE WHEN l.contacted = TRUE OR l.pipeline_stage IN ('PITCHED', 'INTERESTED', 'REPLIED', 'CLOSED') THEN 1 END) as pitched,
                COUNT(CASE WHEN m.has_opened = TRUE THEN 1 END) as opened,
                COUNT(CASE WHEN m.has_clicked = TRUE OR l.pipeline_stage IN ('INTERESTED', 'REPLIED', 'CLOSED') THEN 1 END) as clicked,
                COUNT(CASE WHEN m.has_reply = TRUE OR l.pipeline_stage = 'REPLIED' THEN 1 END) as replied,
                COUNT(CASE WHEN l.pipeline_stage = 'CLOSED' THEN 1 END) as closed
            FROM leads l
            LEFT JOIN (
                SELECT 
                    lead_id,
                    bool_or(opened) as has_opened,
                    bool_or(clicked) as has_clicked,
                    bool_or(is_reply) as has_reply
                FROM message_log
                GROUP BY lead_id
            ) m ON l.id = m.lead_id
            WHERE l.user_id = %s AND l.priority != 'IGNORE'
        """, (user_id,))
        funnel_row = cursor.fetchone()
        funnel_data = dict(funnel_row) if funnel_row else {
            "scouted": 0, "pitched": 0, "opened": 0, "clicked": 0, "replied": 0, "closed": 0
        }

        # 2. Daily Timeline (last 14 days)
        cursor.execute("""
            SELECT 
                DATE(sent_at) as date,
                COUNT(CASE WHEN template_used IN ('website_pitch', 'digital_presence', 'simple_intro', 'custom') THEN 1 END) as whatsapp_count,
                COUNT(CASE WHEN template_used NOT IN ('website_pitch', 'digital_presence', 'simple_intro', 'custom') THEN 1 END) as email_count
            FROM message_log
            WHERE user_id = %s AND sent_at >= CURRENT_DATE - INTERVAL '14 days'
            GROUP BY DATE(sent_at)
            ORDER BY DATE(sent_at) ASC
        """, (user_id,))
        timeline_rows = cursor.fetchall()
        
        # Build timeline map
        timeline_map = {}
        for r in timeline_rows:
            d_str = r['date'].isoformat() if isinstance(r['date'], (date, datetime)) else str(r['date'])
            timeline_map[d_str] = {
                "date": d_str,
                "whatsapp": r['whatsapp_count'],
                "email": r['email_count']
            }
            
        # Ensure we have all last 14 days present
        timeline_list = []
        for i in range(14, -1, -1):
            day = date.today() - timedelta(days=i)
            day_str = day.isoformat()
            if day_str in timeline_map:
                timeline_list.append(timeline_map[day_str])
            else:
                timeline_list.append({
                    "date": day_str,
                    "whatsapp": 0,
                    "email": 0
                })

        # 3. Telemetry Ratios (Open, Click, Reply rates based on total message logs)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sent,
                COUNT(CASE WHEN opened = TRUE THEN 1 END) as total_opened,
                COUNT(CASE WHEN clicked = TRUE THEN 1 END) as total_clicked,
                COUNT(CASE WHEN is_reply = TRUE THEN 1 END) as total_replied
            FROM message_log
            WHERE user_id = %s
        """, (user_id,))
        ratios_row = cursor.fetchone()
        
        open_rate = 0.0
        click_rate = 0.0
        reply_rate = 0.0
        
        if ratios_row and ratios_row['total_sent'] > 0:
            total_sent = ratios_row['total_sent']
            open_rate = round((ratios_row['total_opened'] / total_sent) * 100, 2)
            click_rate = round((ratios_row['total_clicked'] / total_sent) * 100, 2)
            reply_rate = round((ratios_row['total_replied'] / total_sent) * 100, 2)
            
        ratios_data = {
            "open_rate": open_rate,
            "click_rate": click_rate,
            "reply_rate": reply_rate,
            "total_sent": ratios_row['total_sent'] if ratios_row else 0,
            "total_opened": ratios_row['total_opened'] if ratios_row else 0,
            "total_clicked": ratios_row['total_clicked'] if ratios_row else 0,
            "total_replied": ratios_row['total_replied'] if ratios_row else 0
        }

        return jsonify({
            "success": True,
            "funnel": funnel_data,
            "timeline": timeline_list,
            "ratios": ratios_data
        })
    except Exception as e:
        logger.error(f"Error compiling analytics stats: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch analytics: {str(e)}"}), 500
    finally:
        db._release_connection(conn)

@leads_bp.route("/leads/<int:lead_id>/outreach-logs", methods=["GET"])
def get_lead_outreach_logs(lead_id):
    """Fetch outreach logs for a specific lead."""
    logs = db.get_lead_outreach_logs(lead_id, g.user['id'])
    return jsonify(logs)
