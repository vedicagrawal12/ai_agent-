import pytest
import json
from unittest.mock import patch
from collectors.base_collector import Lead

def test_autopilot_campaign_resolved_services(auth_client, db):
    """Verify that generate-email-ai endpoint dynamically resolves to web_design/seo depending on website presence & health."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # 1. Lead with no website
    lead_no_site = Lead(name="No Website Bakery", place_id="place_no_site", website="", city="Bhopal", is_broken_website=False)
    db.save_leads([lead_no_site], user_id)
    
    # 2. Lead with broken website
    lead_broken = Lead(name="Broken Site Salon", place_id="place_broken_site", website="http://broken.com", city="Bhopal", is_broken_website=True)
    db.save_leads([lead_broken], user_id)
    
    # 3. Lead with working website
    lead_working = Lead(name="Working Site Clinic", place_id="place_working_site", website="http://working.com", city="Bhopal", is_broken_website=False)
    db.save_leads([lead_working], user_id)
    
    # Fetch them back from database to have their saved IDs
    all_leads = db.get_all_leads(user_id=user_id)
    saved_no_site = next(l for l in all_leads if l["place_id"] == "place_no_site")
    saved_broken = next(l for l in all_leads if l["place_id"] == "place_broken_site")
    saved_working = next(l for l in all_leads if l["place_id"] == "place_working_site")
    
    # Call Generate Email AI Pitch endpoint with autopilot flag
    with patch("utils.ai_writer.AIOutreachWriter.generate_email_pitch") as mock_writer:
        mock_writer.return_value = "SUBJECT: Dynamic Pitch\nBODY: This is a compiled proposal."
        
        # Test Case 1: No Website
        resp = auth_client.post("/api/outreach/generate-email-ai", json={
            "lead": saved_no_site,
            "tone": "elite",
            "autopilot": True
        }, headers={"X-Gemini-API-Key": "AIzaFakeKey123"})
        
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert resp.json["resolved_service"] == "web_design"
        
        # Test Case 2: Broken Website
        resp = auth_client.post("/api/outreach/generate-email-ai", json={
            "lead": saved_broken,
            "tone": "elite",
            "autopilot": True
        }, headers={"X-Gemini-API-Key": "AIzaFakeKey123"})
        
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert resp.json["resolved_service"] == "web_design"
        
        # Test Case 3: Working Website
        resp = auth_client.post("/api/outreach/generate-email-ai", json={
            "lead": saved_working,
            "tone": "elite",
            "autopilot": True
        }, headers={"X-Gemini-API-Key": "AIzaFakeKey123"})
        
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert resp.json["resolved_service"] == "seo"
