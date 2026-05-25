import requests
import json

class AIOutreachWriter:
    @staticmethod
    def generate_pitch(lead_data: dict, project_sample: str, api_key: str) -> str:
        """
        Generates a highly personalized, human-like sales pitch using the Gemini API.
        Uses raw requests to avoid installing extra dependencies.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        # Build the prompt with an elite system persona
        prompt = f"""
You are an Elite Business Development Consultant & Digital Marketing Expert with 17+ years of experience in helping local Indian businesses establish solid online presence and grow their sales. 

Your goal is to write a highly engaging, warm, professional, and extremely human-like sales outreach pitch. The tone must feel like a genuine recommendation from a friendly consultant, NOT like a pushy salesman or an AI-generated template. Avoid corporate jargon or robotic phrasing. Speak in a natural mix of Hindi and English (conversational Hinglish) that business owners in India easily connect with.

Here are the details of the local business we are reaching out to:
- Business Name: {lead_data.get('name', 'Business')}
- Industry: {lead_data.get('category', 'Business')}
- City: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')} stars
- Google Maps Reviews Count: {lead_data.get('reviews', '0')} reviews
- Website Status: They do NOT have a website yet. (This is a huge opportunity they are missing!)

Here is the best matching sample of my previous work that you must mention as proof:
- Portfolio Work Sample: {project_sample}

Strict Marketer Copywriting Guidelines:
1. Act as a Helpful Advisor: Kabhi bhi pushy ya generic spammer ki tarah sound mat karein. Unhe samjhayein ki unka business bohot badhiya hai par website na hone se customer competitors ke paas ja rahe hain.
2. Appreciate first: Pehle unke business ki Google Maps rating aur reviews ki tareef karein (taaki positive note par start ho).
3. Soft Gap Pitch: "Maine notice kiya ki Google par search karne pe aapki website nahi mili..." is line ko bohot smooth aur polite tarike se mention karein.
4. Seamlessly integrate the project sample: Jo portfolio sample link/text diya hai, use bilkul naturally fit karein (e.g., "Maine haal hi mein isi category ke business ke liye ek interactive portal build kiya hai...").
5. clear Call to Action: Conversation end karte samay ek direct par comfortable call to action dein (e.g. "Kya hum kal ek 2-minute ki choti discussion ya call kar sakte hain?").
6. Keep it formatted: WhatsApp messages me readability ke liye line breaks, short paragraphs aur emojis (like 👋, 🎯, 🌐, 📈) ka natural aur balanced use karein.
7. Absolutely No Placeholders: Final output me koi bhi [Your Name], [Insert Link], ya brackets/tags mat chhodna. Message bilkul ready-to-send hona chahiye.
"""

        # Models to try in order of fallback preference
        models = [
            ("v1", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-flash-latest"),
            ("v1", "gemini-1.5-pro"),
            ("v1beta", "gemini-pro")
        ]

        last_error = ""
        for version, model in models:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 800
                }
            }

            try:
                print(f"Trying Gemini model: {model} on {version}...")
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            print(f"Success with Gemini model: {model}!")
                            return text.strip()
                
                # Fetch detailed error response if available
                try:
                    error_data = response.json()
                    last_error = error_data.get("error", {}).get("message", f"Status {response.status_code}")
                except:
                    last_error = f"Status {response.status_code}"
                print(f"Model {model} on {version} failed: {last_error}")
                
            except requests.exceptions.Timeout:
                last_error = "Request timed out."
                print(f"Model {model} timed out.")
            except Exception as e:
                last_error = str(e)
                print(f"Network error with model {model}: {last_error}")

        raise Exception(f"All Gemini models failed. Last error: {last_error}")
