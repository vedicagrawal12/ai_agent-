import requests
import json
import sqlite3

def test_api():
    url = "http://localhost:5000/api/outreach/generate-whatsapp"
    headers = {
        "Content-Type": "application/json",
        "X-Gemini-API-Key": "test_key" # just to see if we hit auth or another error
    }
    payload = {
        "lead": {"name": "Test Business"},
        "tone": "casual",
        "service": "SEO",
        "language": "english",
        "sender": {"name": "Test", "brand": "Test Brand"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        print("Status:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Failed to connect to local server:", e)

if __name__ == "__main__":
    test_api()
