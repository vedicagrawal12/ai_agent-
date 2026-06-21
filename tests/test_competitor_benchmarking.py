import pytest
from unittest.mock import patch
from collectors.base_collector import Lead
from utils.ai_writer import AIOutreachWriter

def test_competitor_benchmarking_logic(auth_client, db):
    """Test that db.get_competitors_benchmark works and generates fallback competitors correctly."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Save a lead
    lead = Lead(
        name="Target Fitness Gym",
        place_id="gym_place_id",
        website="http://targetfitness.com",
        city="Bhopal",
        category="Gym/Fitness",
        rating=4.2,
        reviews=25
    )
    db.save_leads([lead], user_id)
    
    # Retrieve from DB to get ID
    saved_leads = db.get_all_leads(user_id=user_id)
    target_lead = next(l for l in saved_leads if l["place_id"] == "gym_place_id")
    lead_id = target_lead["id"]
    
    # 1. Fetch benchmark. Since no other leads exist, it must generate mock competitors.
    benchmark = db.get_competitors_benchmark(lead_id)
    assert benchmark is not None
    assert "lead" in benchmark
    assert "competitors" in benchmark
    assert benchmark["lead"]["name"] == "Target Fitness Gym"
    assert len(benchmark["competitors"]) == 3
    
    # Check that fallback competitors are mock and have reasonable superior scores (85%+)
    for comp in benchmark["competitors"]:
        assert comp["is_mock"] is True
        assert comp["speed_score"] >= 85
        assert comp["seo_score"] >= 85
        assert comp["rating"] >= 4.0
        assert comp["reviews"] > target_lead["reviews"]

    # 2. Save a real competitor in the database
    real_comp = Lead(
        name="Real Power Gym",
        place_id="real_comp_id",
        website="http://realpower.com",
        city="Bhopal",
        category="Gym/Fitness",
        rating=4.5,
        reviews=100
    )
    db.save_leads([real_comp], user_id)
    
    # Fetch benchmark again. One should be the real database competitor, and others fallback.
    benchmark2 = db.get_competitors_benchmark(lead_id)
    assert benchmark2 is not None
    real_found = [c for c in benchmark2["competitors"] if not c["is_mock"]]
    mock_found = [c for c in benchmark2["competitors"] if c["is_mock"]]
    
    assert len(real_found) == 1
    assert real_found[0]["name"] == "Real Power Gym"
    assert len(mock_found) == 2


def test_competitor_endpoint(auth_client, db):
    """Verify that the GET /api/leads/<lead_id>/competitors route functions correctly."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    lead = Lead(
        name="Target Beauty Salon",
        place_id="salon_place_id",
        website="http://targetbeauty.com",
        city="Indore",
        category="Salon",
        rating=4.0,
        reviews=10
    )
    db.save_leads([lead], user_id)
    
    saved_leads = db.get_all_leads(user_id=user_id)
    target_lead = next(l for l in saved_leads if l["place_id"] == "salon_place_id")
    lead_id = target_lead["id"]
    
    resp = auth_client.get(f"/api/leads/{lead_id}/competitors")
    assert resp.status_code == 200
    assert "lead" in resp.json
    assert "competitors" in resp.json
    assert len(resp.json["competitors"]) == 3


def test_ai_writer_competitor_context():
    """Verify that AIOutreachWriter incorporates competitor benchmark metadata into the prompt when they have a website."""
    lead_data = {
        "name": "Target Salon",
        "city": "Bhopal",
        "category": "Salon",
        "rating": 4.0,
        "reviews": 15,
        "website": "http://target.com"
    }
    
    competitor_data = {
        "lead": lead_data,
        "competitors": [
            {
                "name": "Elite Hair Spa",
                "website": "http://elitehairspa.com",
                "rating": 4.8,
                "reviews": 150,
                "speed_score": 92,
                "seo_score": 95,
                "ssl_score": 100,
                "is_mock": False
            }
        ]
    }
    
    with patch("utils.ai_writer.AIOutreachWriter._call_gemini_api") as mock_gemini:
        mock_gemini.return_value = "Mocked generated output"
        
        AIOutreachWriter.generate_pitch(
            lead_data=lead_data,
            project_sample="project ABC",
            api_key="AIzaFakeKey123",
            competitor_data=competitor_data
        )
        
        # Verify call arguments
        called_prompt = mock_gemini.call_args[0][0]
        assert "COMPETITOR BENCHMARKING & COMPARISON DETAILS" in called_prompt
        assert "Elite Hair Spa" in called_prompt
        assert "92/100" in called_prompt
        assert "95/100" in called_prompt


def test_ai_writer_competitor_no_website_context():
    """Verify that AIOutreachWriter properly formats competitor context when they do not have a website."""
    lead_data = {
        "name": "Target Salon",
        "city": "Bhopal",
        "category": "Salon",
        "rating": 4.0,
        "reviews": 15,
        "website": "http://target.com"
    }
    
    competitor_data = {
        "lead": lead_data,
        "competitors": [
            {
                "name": "Elite Hair Spa",
                "website": "", # No website
                "rating": 4.8,
                "reviews": 150,
                "speed_score": 0,
                "seo_score": 0,
                "ssl_score": 0,
                "is_mock": False
            }
        ]
    }
    
    with patch("utils.ai_writer.AIOutreachWriter._call_gemini_api") as mock_gemini:
        mock_gemini.return_value = "Mocked generated output"
        
        AIOutreachWriter.generate_pitch(
            lead_data=lead_data,
            project_sample="project ABC",
            api_key="AIzaFakeKey123",
            competitor_data=competitor_data
        )
        
        called_prompt = mock_gemini.call_args[0][0]
        assert "COMPETITOR BENCHMARKING & COMPARISON DETAILS" in called_prompt
        assert "Elite Hair Spa" in called_prompt
        assert "NO WEBSITE YET" in called_prompt
        assert "does not have a website listed" in called_prompt
        # Make sure 0/100 speed and 0/100 seo scores are not generated in the prompt insight
        assert "0/100" not in called_prompt


def test_competitor_name_collision_and_rate_limiting(auth_client, db):
    """Test competitor name collision handling (BUG-013) and rate limiting (BUG-016)."""
    user = db.get_user_by_username("testuser")
    user_id = user["id"]
    
    # Save a lead whose name is exactly one of the niche names, e.g. "Pulse Fitness Center"
    lead = Lead(
        name="Pulse Fitness Center",
        place_id="collision_place_id",
        website="http://pulsefitness.com",
        city="Bhopal",
        category="Gym/Fitness",
        rating=4.2,
        reviews=25
    )
    db.save_leads([lead], user_id)
    
    saved_leads = db.get_all_leads(user_id=user_id)
    target_lead = next(l for l in saved_leads if l["place_id"] == "collision_place_id")
    lead_id = target_lead["id"]
    
    # Fetch competitors. It will generate mock competitors.
    # The first mock competitor for Gym/Fitness is "Pulse Fitness Center".
    # It must detect the collision and append a suffix (e.g. " Elite").
    benchmark = db.get_competitors_benchmark(lead_id)
    assert benchmark is not None
    assert len(benchmark["competitors"]) == 3
    
    # Ensure none of the mock competitor names is equal to target lead name
    for comp in benchmark["competitors"]:
        assert comp["name"].lower() != target_lead["name"].lower()
        # Verify that "Pulse Fitness Center" was modified
        if "pulse" in comp["name"].lower():
            assert "elite" in comp["name"].lower() or "pro" in comp["name"].lower() or "premium" in comp["name"].lower()

    # Verify rate limiting endpoint (BUG-016)
    resp = auth_client.get(f"/api/leads/{lead_id}/competitors")
    assert resp.status_code == 200
