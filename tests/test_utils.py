# pyrefly: ignore [missing-import]
import pytest
from utils.data_cleaner import DataCleaner
from utils.email_scraper import EmailScraper
from collectors.base_collector import Lead

def test_phone_standardization():
    """Verify raw phone digits are standardized into visual layouts."""
    assert DataCleaner.standardize_phone("9876543210") == "+91 98765 43210"
    assert DataCleaner.standardize_phone("09876543210") == "+91 98765 43210"
    assert DataCleaner.standardize_phone("+919876543210") == "+91 98765 43210"
    # Fallback/unrecognized
    assert DataCleaner.standardize_phone("+1234567") == "+1234567"
    assert DataCleaner.standardize_phone("") == ""

def test_phone_classification():
    """Verify phone validation and line type classification using phonenumbers."""
    # Valid Indian mobile number
    data1 = DataCleaner.validate_and_classify_phone("+919876543210")
    assert data1["is_valid"] is True
    assert data1["whatsapp_number"] == "919876543210"
    assert data1["line_type"] == "MOBILE"

    # Valid Indian landline number (Bhopal local)
    data2 = DataCleaner.validate_and_classify_phone("07552443000")
    assert data2["is_valid"] is True
    assert data2["line_type"] == "LANDLINE"

    # Invalid number
    data3 = DataCleaner.validate_and_classify_phone("12345")
    assert data3["is_valid"] is False

def test_email_validation():
    """Verify cleaning and valid vs blocked pattern validation."""
    assert EmailScraper.is_valid_email("contact@mybusiness.co.in") is True
    assert EmailScraper.is_valid_email("info@test.com.") is True  # trailing dot is cleaned
    
    # Excluded patterns
    assert EmailScraper.is_valid_email("sentry@mybusiness.com") is False
    assert EmailScraper.is_valid_email("test@domain.com") is False
    assert EmailScraper.is_valid_email("image.png") is False

def test_ssrf_blocking():
    """Verify SSRF checks block localhost/private hostnames/IP ranges and permit public ones."""
    # Loopback & link-local blocks
    assert EmailScraper._is_safe_url("http://localhost:5000") is False
    assert EmailScraper._is_safe_url("https://127.0.0.1/admin") is False
    assert EmailScraper._is_safe_url("http://metadata.google.internal") is False
    
    # Private IP range blocks
    assert EmailScraper._is_safe_url("http://192.168.1.100/index.html") is False
    assert EmailScraper._is_safe_url("http://10.0.0.1") is False
    
    # Public domain allows
    assert EmailScraper._is_safe_url("https://google.com") is True
    assert EmailScraper._is_safe_url("http://github.com/test") is True

def test_priority_assignment():
    """Verify business priority assignment based on reviews, phone, and broken website flags."""
    # 1. Has working website -> IGNORE
    lead1 = Lead(name="A", website="http://working.com", reviews=10, phone="+919876543210", is_broken_website=False)
    assert DataCleaner.assign_priority(lead1) == "IGNORE"
    
    # 2. Broken website, <50 reviews, has phone -> HIGH
    lead2 = Lead(name="B", website="http://broken.com", reviews=20, phone="+919876543210", is_broken_website=True)
    assert DataCleaner.assign_priority(lead2) == "HIGH"
    
    # 3. No website, <50 reviews, has phone -> HIGH
    lead3 = Lead(name="C", website="", reviews=30, phone="+919876543210", is_broken_website=False)
    assert DataCleaner.assign_priority(lead3) == "HIGH"
    
    # 4. No website, 50-200 reviews, has phone -> MEDIUM
    lead4 = Lead(name="D", website="", reviews=100, phone="+919876543210", is_broken_website=False)
    assert DataCleaner.assign_priority(lead4) == "MEDIUM"
    
    # 5. No website, >200 reviews, has phone -> LOW
    lead5 = Lead(name="E", website="", reviews=250, phone="+919876543210", is_broken_website=False)
    assert DataCleaner.assign_priority(lead5) == "LOW"

def test_remove_duplicates():
    """Verify deduplication removes matching place_id, phone, or name + city."""
    leads = [
        # Match place_id
        Lead(name="Gym Alpha", place_id="place_abc", phone="+919876543210", city="Bhopal"),
        Lead(name="Gym Alpha Dup", place_id="place_abc", phone="", city="Bhopal"),
        
        # Match standardized phone
        Lead(name="Gym Beta", place_id="place_b1", phone="+91 99999 99999", city="Bhopal"),
        Lead(name="Gym Beta Dup", place_id="place_b2", phone="09999999999", city="Bhopal"),
        
        # Match normalized name + city
        Lead(name="Gym Gamma", place_id="place_g1", phone="", city="Bhopal"),
        Lead(name=" gym gamma  ", place_id="place_g2", phone="", city="Bhopal"),
        
        # Unique
        Lead(name="Gym Delta", place_id="place_unique", phone="", city="Bhopal")
    ]
    
    # Pre-standardize phone numbers just like clean_leads does
    for lead in leads:
        lead.phone = DataCleaner.standardize_phone(lead.phone)
        
    cleaned = DataCleaner.remove_duplicates(leads)
    assert len(cleaned) == 4
    names = {l.name.strip() for l in cleaned}
    assert "Gym Alpha" in names
    assert "Gym Beta" in names
    assert "Gym Gamma" in names
    assert "Gym Delta" in names
