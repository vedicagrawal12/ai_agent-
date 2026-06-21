# pyrefly: ignore [missing-import]
import pytest
import json
from unittest.mock import patch, MagicMock
from collectors.base_collector import Lead
from utils.website_auditor import audit_website
from utils.ai_writer import AIOutreachWriter

def test_audit_website_logic():
    """Verify website auditor logic: scores and recommendations calculation."""
    html_content = """
    <html>
      <head>
        <title>Excellent Local Bakery - Fresh Bread & Pastries</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Looking for the best bakery in town? We serve fresh hot bread, croissants, custom cakes, and delicious coffee daily. Come visit us today!">
      </head>
      <body>
        <h1>Welcome to Excellent Local Bakery</h1>
        <img src="pastry.png" alt="Delicious Pastry">
        <img src="cake.jpg"> <!-- Missing alt tag -->
      </body>
    </html>
    """
    
    with patch("requests.get") as mock_get:
        # 1. Test standard successful HTTPS scan
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_get.return_value = mock_response
        
        results = audit_website("https://excellentbakery.com")
        
        assert results["overall_score"] > 0
        assert results["metrics"]["ssl_configured"] is True
        assert results["metrics"]["has_viewport"] is True
        assert results["metrics"]["title_length"] == len("Excellent Local Bakery - Fresh Bread & Pastries")
        assert results["metrics"]["meta_description_length"] == len("Looking for the best bakery in town? We serve fresh hot bread, croissants, custom cakes, and delicious coffee daily. Come visit us today!")
        assert results["metrics"]["h1_count"] == 1
        assert results["metrics"]["total_images"] == 2
        assert results["metrics"]["images_with_alt"] == 1
        
        # Checking alt tag score = 50%
        assert results["scores"]["alt"] == 50
        assert results["scores"]["ssl"] == 100
        assert results["scores"]["mobile"] == 100
        
        # Verify recommendation has alt tags warning
        rec_titles = [rec["title"] for rec in results["recommendations"]]
        assert any("Missing Alt Tags" in t for t in rec_titles)
        
        # 2. Test SSL handshake failure / HTTP fallback
        mock_get.side_effect = Exception("Connection Failed")
        results_err = audit_website("http://broken-site.com")
        assert results_err["scores"]["ssl"] == 0
        assert results_err["scores"]["speed"] == 0
        assert results_err["overall_score"] < 30
        assert any("SSL Missing" in rec["title"] or "Connection Failed" in rec["title"] for rec in results_err["recommendations"])

def test_audit_endpoint(auth_client, db):
    """Verify POST /api/leads/<id>/audit executes scan and updates DB."""
    # Create test lead with website
    user = db.get_user_by_username("testuser")
    lead = Lead(name="Test Audit Gym", place_id="place_audit", website="https://testauditgym.com", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    html_mock = "<html><head><title>Test Gym</title></head><body><h1>Hello</h1></body></html>"
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_mock
        mock_get.return_value = mock_response
        
        resp = auth_client.post(f"/api/leads/{saved_lead['id']}/audit")
        
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert "audit_data" in resp.json
        assert resp.json["audit_data"]["overall_score"] > 0
        
        # Verify database column was updated
        updated_lead = db.get_lead_by_id(saved_lead["id"], user_id=user["id"])
        assert updated_lead["audit_data"] != ""
        
        # Verify JSON can be parsed
        parsed_db_audit = json.loads(updated_lead["audit_data"])
        assert parsed_db_audit["overall_score"] == resp.json["audit_data"]["overall_score"]

def test_public_audit_report_page(client, db):
    """Verify GET /audit/<id> is public and renders report card correctly."""
    # Register/fetch testuser
    client.post('/signup', data={'username': 'testuser', 'email': 'test@example.com', 'password': 'password123', 'confirm_password': 'password123', 'phone': '1234567890'})
    user = db.get_user_by_username("testuser")
    
    # Save a lead and inject mock audit data
    audit_payload = {
        "audited_at": "2026-06-12 18:00:00",
        "url": "https://pubgym.com",
        "overall_score": 88,
        "status_code": 200,
        "metrics": {
            "response_time": 0.45,
            "ssl_configured": True,
            "has_viewport": True,
            "title_length": 45,
            "meta_description_length": 140,
            "h1_count": 1,
            "total_images": 5,
            "images_with_alt": 4
        },
        "scores": {
            "speed": 100,
            "seo": 90,
            "mobile": 100,
            "ssl": 100,
            "alt": 80
        },
        "recommendations": [
            {
                "type": "warning",
                "category": "SEO",
                "title": "Missing Alt Tags (1 image)",
                "description": "Ensure all images have alt text."
            }
        ]
    }
    
    lead = Lead(name="Public Gym", place_id="place_pub", website="https://pubgym.com", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    db.update_lead_audit_data(saved_lead["id"], json.dumps(audit_payload), user_id=user["id"])
    
    # Verify public unauthenticated access
    resp = client.get(f"/audit/{saved_lead['id']}")
    assert resp.status_code == 200
    
    # Check that template content rendering is present
    html_text = resp.data.decode("utf-8")
    assert "Public Gym" in html_text
    assert "88" in html_text
    assert "Public Audit Report URL" not in html_text # Check that internal directives aren't leaked, but logo/branding is:
    assert "Roadmap" in html_text
    assert "Scan Diagnostics" in html_text

def test_outreach_ai_generation_with_audit(auth_client, db):
    """Verify AI pitch writer includes audit link and metrics when audit_data exists."""
    user = db.get_user_by_username("testuser")
    
    audit_payload = {
        "overall_score": 42,
        "scores": {"speed": 30, "seo": 50, "mobile": 0, "ssl": 0, "alt": 0},
        "recommendations": [
            {"type": "error", "category": "Security", "title": "SSL Missing", "description": "Uses HTTP instead of HTTPS"},
            {"type": "error", "category": "Mobile", "title": "Mobile viewport missing", "description": "Not optimized for phone screens"}
        ]
    }
    
    lead = Lead(name="Slow Gym", place_id="place_slow", website="https://slowgym.com", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    db.update_lead_audit_data(saved_lead["id"], json.dumps(audit_payload), user_id=user["id"])
    
    # Call Generate AI Pitch endpoint
    with patch("utils.ai_writer.AIOutreachWriter._call_gemini_api") as mock_gemini:
        mock_gemini.return_value = "Mocked Pitch containing audit URL and warning details."
        
        resp = auth_client.post("/api/outreach/generate-ai", json={
            "lead": {"id": saved_lead["id"], "name": "Slow Gym", "city": "Bhopal", "category": "Gym"},
            "tone": "elite",
            "length": "detailed",
            "service": "web_design"
        }, headers={"X-Gemini-API-Key": "AIzaFakeKey123"})
        
        assert resp.status_code == 200
        assert resp.json["success"] is True
        
        # Verify mock gemini call argument contains our audit_data instructions
        args, kwargs = mock_gemini.call_args
        prompt_sent = args[0]
        
        assert "WEBSITE SEO & PERFORMANCE AUDIT RESULTS" in prompt_sent
        assert "overall_score" not in prompt_sent # Prompt formatted should contain:
        assert "Overall Site Score: 42/100" in prompt_sent
        assert "/audit/" in prompt_sent
        assert "Mobile viewport missing" in prompt_sent
        assert "SSL Missing" in prompt_sent


def test_outreach_ai_generation_micro_limit(auth_client, db):
    """Verify AI pitch writer constructs a simplified brief prompt when min_words <= 100."""
    user = db.get_user_by_username("testuser")
    
    audit_payload = {
        "overall_score": 42,
        "scores": {"speed": 30, "seo": 50, "mobile": 0, "ssl": 0, "alt": 0},
        "recommendations": [
            {"type": "error", "category": "Security", "title": "SSL Missing", "description": "Uses HTTP instead of HTTPS"}
        ]
    }
    
    # Save a lead
    lead = Lead(name="Slow Gym", place_id="place_slow", website="https://slowgym.com", city="Bhopal")
    db.save_leads([lead], user["id"])
    saved_lead = db.get_all_leads(user_id=user["id"])[0]
    
    db.update_lead_audit_data(saved_lead["id"], json.dumps(audit_payload), user_id=user["id"])
    
    # Call Generate AI Pitch endpoint with min_words=50
    with patch("utils.ai_writer.AIOutreachWriter._call_gemini_api") as mock_gemini:
        mock_gemini.return_value = "Mocked concise pitch."
        
        resp = auth_client.post("/api/outreach/generate-ai", json={
            "lead": {"id": saved_lead["id"], "name": "Slow Gym", "city": "Bhopal", "category": "Gym"},
            "tone": "elite",
            "length": "detailed",
            "service": "web_design",
            "min_words": 50
        }, headers={"X-Gemini-API-Key": "AIzaFakeKey123"})
        
        assert resp.status_code == 200
        assert resp.json["success"] is True
        
        args, kwargs = mock_gemini.call_args
        prompt_sent = args[0]
        
        # Verify simplified audit directive is included
        assert "WEBSITE SEO & PERFORMANCE AUDIT RESULTS" in prompt_sent
        assert "Keep it extremely brief and direct due to strict word limit constraints" in prompt_sent
        
        # Verify detailed scores and recommendations are NOT in the prompt
        assert "Category Scores:" not in prompt_sent
        assert "SSL Missing" not in prompt_sent
        
        # Verify strict word limit constraint message is in length directives
        assert "strictly be between 50 and 75 words total" in prompt_sent
        assert "condense or skip detailed descriptions" in prompt_sent

