import os

# Append to ai_writer.py
ai_writer_code = """

    @staticmethod
    def generate_whatsapp_direct(lead_data: dict, api_key: str, tone: str, service: str, sender_info: dict, language: str) -> str:
        \"\"\"Generates a standalone, punchy WhatsApp pitch.\"\"\"
        if not api_key:
            raise Exception("Gemini API key is required.")
            
        business_name = lead_data.get('name', 'Business Owner')
        sender_name = sender_info.get('name', '')
        sender_brand = sender_info.get('brand', '')
        
        prompt = f\"\"\"
You are {sender_name} from {sender_brand}, an expert in {service}.
Write a direct, punchy, and highly conversational WhatsApp outreach message to {business_name}.

The goal is to pitch {service} to them. Keep it very short (under 75 words).
Use emojis sparingly but effectively.
Tone: {tone}
Language: {language}

Output ONLY the exact WhatsApp message text. No placeholders, no quotes, no extra text.
\"\"\"
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
"""

with open('utils/ai_writer.py', 'a', encoding='utf-8') as f:
    f.write(ai_writer_code)

# Append to api_outreach.py
api_outreach_code = """

@outreach_bp.route("/outreach/generate-whatsapp", methods=["POST"])
@limiter.limit("30 per minute")
def generate_whatsapp_standalone():
    gemini_key = request.headers.get("X-Gemini-API-Key")
    if not gemini_key:
        return jsonify({"error": "Gemini API key is missing."}), 401
        
    data = request.get_json() or {}
    lead_data = data.get("lead", {})
    tone = data.get("tone", "elite")
    service = data.get("service", "web_design")
    sender = data.get("sender", {})
    language = data.get("language", "hinglish")
    
    if not lead_data:
        return jsonify({"error": "Lead data is required"}), 400
        
    try:
        from utils.ai_writer import AIOutreachWriter
        message = AIOutreachWriter.generate_whatsapp_direct(
            lead_data=lead_data,
            api_key=gemini_key,
            tone=tone,
            service=service,
            sender_info=sender,
            language=language
        )
        return jsonify({"success": True, "message": message})
    except Exception as e:
        logger.error(f"Error generating WhatsApp message: {e}")
        return jsonify({"error": str(e)}), 500
"""

with open('routes/api_outreach.py', 'a', encoding='utf-8') as f:
    f.write(api_outreach_code)

print("Successfully injected WhatsApp generate endpoints")
