import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"
EMAIL = "vedicagrawalmva@gmail.com"
PASSWORD = "12345678"
GEMINI_API_KEY = "AQ.Ab8RN6LiRHmAcqutnxqov0hMGsZ6MR-cpCT_ZMG8GjLIZA4ZtQ"

session = requests.Session()
csrf_token = ""

def print_section(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def run_test(name, func):
    print(f"--- Running Test: {name} ---")
    try:
        func()
        print(f"[SUCCESS] {name}\n")
    except Exception as e:
        print(f"[ERROR] {name} failed: {e}\n")

def initialize_session():
    global csrf_token
    # First request to get the CSRF cookie
    res = session.get(f"{BASE_URL}/login")
    csrf_token = session.cookies.get('csrf_token')

def test_signup_or_login():
    global csrf_token
    headers = {"X-CSRF-Token": csrf_token}
    # Try login first
    res = session.post(f"{BASE_URL}/login", data={"email": EMAIL, "password": PASSWORD}, headers=headers)
    if res.status_code == 200:
        print("Login successful.")
        csrf_token = session.cookies.get('csrf_token') or csrf_token
        return
        
    print("Login failed, attempting signup...")
    # Try signup
    res = session.post(f"{BASE_URL}/signup", data={"username": "Vedic Agrawal", "email": EMAIL, "password": PASSWORD, "phone": "9999999999"}, headers=headers)
    if res.status_code == 200:
        print("Signup successful.")
        csrf_token = session.cookies.get('csrf_token') or csrf_token
    else:
        raise Exception(f"Signup and Login failed: {res.status_code} {res.text}")

def test_search():
    global csrf_token
    headers = {"X-CSRF-Token": csrf_token}
    data = {
        "query": "gym",
        "city": "Mumbai",
        "max_results": 2,
        "include_with_website": False,
        "hide_saved": False,
        "deep_scan": False,
        "zones": []
    }
    res = session.post(f"{BASE_URL}/api/search", json=data, headers=headers)
    if res.status_code != 202:
        raise Exception(f"Search initiation failed: {res.status_code} {res.text}")
    task_id = res.json().get('task_id')
    print(f"Search task initiated: {task_id}")
    
    for _ in range(30):
        status_res = session.get(f"{BASE_URL}/api/search/status/{task_id}")
        if status_res.status_code == 200:
            status_data = status_res.json()
            if status_data.get('status') == 'DONE':
                result = status_data.get('result', {})
                print(f"Search completed. Found {result.get('stats', {}).get('leads_count', 0)} new leads.")
                return result
            elif status_data.get('status') == 'ERROR':
                raise Exception(f"Search error: {status_data.get('message')}")
        time.sleep(2)
    raise Exception("Search timed out")

def test_get_leads():
    res = session.get(f"{BASE_URL}/api/leads?page=1&per_page=10")
    if res.status_code == 200:
        data = res.json()
        print(f"Fetched {len(data.get('leads', []))} leads.")
        if data.get('leads'):
            return data['leads'][0]['id']
    else:
        raise Exception(f"Failed to fetch leads: {res.status_code} {res.text}")
    return None

def test_audit(lead_id):
    if not lead_id: return
    headers = {"X-CSRF-Token": csrf_token}
    res = session.post(f"{BASE_URL}/api/leads/{lead_id}/audit", headers=headers)
    print(f"Audit response: {res.status_code} {res.text[:100]}...")
    if res.status_code != 200: raise Exception(f"Audit failed: {res.status_code}")

def test_gemini_pitch(lead_id):
    if not lead_id: return
    data = {
        "lead": {"id": lead_id, "name": "Test Business", "city": "Mumbai", "reviews": 10, "rating": 4.5},
        "project_sample": "https://example.com/demo",
        "tone": "elite",
        "length": "detailed",
        "service": "web_design",
        "sender": {"name": "Vedic", "brand": "Agency", "role": "CEO"},
        "min_words": 100,
        "language": "hinglish"
    }
    headers = {"X-Gemini-API-Key": GEMINI_API_KEY, "X-CSRF-Token": csrf_token}
    res = session.post(f"{BASE_URL}/api/outreach/generate-ai", json=data, headers=headers)
    if res.status_code == 200:
        print("Gemini Pitch successful:\n", res.json().get('pitch')[:100] + "...")
    else:
        raise Exception(f"Gemini Pitch failed: {res.status_code} {res.text}")

def test_email_scrape(lead_id):
    if not lead_id: return
    headers = {"X-CSRF-Token": csrf_token}
    res = session.post(f"{BASE_URL}/api/leads/{lead_id}/scan-email", headers=headers)
    print(f"Email scrape response: {res.status_code} {res.text[:100]}...")

def test_dashboard_stats():
    res = session.get(f"{BASE_URL}/api/stats/analytics")
    print(f"Analytics response: {res.status_code} {res.text[:100]}...")

if __name__ == "__main__":
    print_section("STARTING TEST HARNESS")
    initialize_session()
    run_test("Login/Signup", test_signup_or_login)
    
    lead_result = None
    def do_search():
        global lead_result
        lead_result = test_search()
    
    run_test("Lead Search", do_search)
    
    first_lead_id = None
    def do_get_leads():
        global first_lead_id
        first_lead_id = test_get_leads()
        print(f"Using Lead ID {first_lead_id} for further tests.")
        
    run_test("Get Leads", do_get_leads)
    
    run_test("Website Audit", lambda: test_audit(first_lead_id))
    run_test("Gemini Pitch Gen", lambda: test_gemini_pitch(first_lead_id))
    run_test("Email Scrape", lambda: test_email_scrape(first_lead_id))
    run_test("Analytics Telemetry", test_dashboard_stats)
    print_section("TEST HARNESS COMPLETE")
