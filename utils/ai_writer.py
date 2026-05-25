import requests
import json

class AIOutreachWriter:
    @staticmethod
    def generate_pitch(
        lead_data: dict, 
        project_sample: str, 
        api_key: str,
        tone: str = "elite",
        length: str = "detailed",
        sender_info: dict = None,
        refine_feedback: str = None,
        previous_pitch: str = None
    ) -> str:
        """
        Generates a highly personalized, human-like sales pitch using the Gemini API.
        Uses raw requests to avoid installing extra dependencies.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        # Resolve tone directives
        tone_directives = ""
        if tone == "friendly":
            tone_directives = """
- PERSONA: Warm, enthusiastic, super friendly local freelance developer who is eager to help.
- TONE: Casual, extremely polite, helpful, very human. Speak like a friendly tech-savvy neighbor in Hinglish.
- VALUE ADD: Appreciates their business's popularity naturally. Avoids looking like a corporate agency.
- CTA: Offers a super quick video recording or link of a homepage mockup layout made specifically for them.
"""
        elif tone == "direct":
            tone_directives = """
- PERSONA: Sharp, metric-driven local digital growth partner.
- TONE: Highly direct, business-focused, professional, metric-heavy, polite but fast-paced.
- VALUE ADD: Focuses heavily on customer booking leakages and search engine visibility.
- CTA: Offers a quick look at a raw digital storefront layout draft, zero commitments.
"""
        else: # elite
            tone_directives = """
- PERSONA: Elite Business Development Consultant & Web Strategy Expert.
- TONE: Highly professional, polite, warm, growth-focused, extremely authoritative yet friendly.
- VALUE ADD: Appreciates high review volume and pivots into digital customer conversion gaps.
- CTA: Offers to share a premium custom-sketched homepage raw mockup/draft layout for their brand.
"""

        # Resolve length directives
        length_directives = ""
        if length == "short":
            length_directives = """
- LENGTH: Extremely brief and DM-friendly (maximum 2-3 very short sentences/paragraphs, under 90 words total).
- STRUCTURE: Hook them, drop the gap, state the matched portfolio proof sentence, and ask the CTA. Keep it ultra-compact so they don't have to scroll on mobile.
"""
        else: # detailed
            length_directives = """
- LENGTH: Detailed and structured (3-4 crisp, mobile-friendly paragraphs).
- STRUCTURE: Beautiful flow starting with a warm hook, explaining the conversion gap logically, presenting the matched work sample, and concluding with an irresistible mockup draft offer.
"""

        # Resolve smart review count hooks
        try:
            reviews_count = int(lead_data.get('reviews', 0))
        except (ValueError, TypeError):
            reviews_count = 0
        
        if reviews_count >= 100:
            hook_type_directive = f"""
- SMART HOOK (ESTABLISHED AUTHORITY): This local business has a massive review count ({reviews_count} reviews) and is clearly an established local favourite. Frame the pitch around scaling, automating reservations, and retaining premium customers who prefer quick booking interfaces. (e.g. 'Aap Bhopal ke elite brands mein aate hain...').
"""
        else:
            hook_type_directive = f"""
- SMART HOOK (TRUST & CREDIBILITY BUILDER): This business is newly growing or has low digital proof ({reviews_count} reviews). Frame the pitch around building massive trust, credibility, first impression power, and getting new customers in {lead_data.get('city', 'your city')} using a professional digital storefront.
"""

        # Resolve sender profile sign-off
        name = sender_info.get("name", "").strip() if sender_info else ""
        brand = sender_info.get("brand", "").strip() if sender_info else ""
        role = sender_info.get("role", "").strip() if sender_info else ""
        
        signoff_directive = ""
        if name or brand or role:
            signoff_parts = []
            if name:
                signoff_parts.append(name)
            if role:
                signoff_parts.append(f"({role})")
            if brand:
                signoff_parts.append(f"at {brand}")
            
            signoff_str = " ".join(signoff_parts)
            signoff_directive = f"\n7. SIGN OFF: Sign off the message naturally as '{signoff_str}' (e.g. 'Best, {name}' or similar, keeping it friendly)."
        else:
            signoff_directive = f"\n7. NO SIGN OFF: Do NOT sign off the message with any name or brand placeholder. Leave it open or end on a friendly CTA."

        # Build the prompt with dynamic context
        if refine_feedback and previous_pitch:
            prompt = f"""
You are an Elite B2B Pitch Copywriter. Your task is to REFINE and REWRITE an existing cold outreach sales pitch based on direct feedback from the user.

Here are the details of the local business we are pitching:
- Business Name: {lead_data.get('name', 'Business')}
- City: {lead_data.get('city', 'your city')}
- Category: {lead_data.get('category', 'Business')}

Here is the PREVIOUS generated sales pitch:
---------------------------------
{previous_pitch}
---------------------------------

Here is the USER'S FEEDBACK/REWRITE REQUEST:
---------------------------------
"{refine_feedback}"
---------------------------------

Strict Copywriting Guidelines for Refinement:
1. Apply the user's feedback precisely (e.g. making it shorter, translating to a specific language, adding more emojis, changing the focus, etc.).
2. Keep the natural, conversational, polite Hinglish/English tone.
3. Preserve the core business personalization details (Reviews/Rating/Name/City) and ensure the dynamic project sample is still naturally included.
4. Keep the output beautifully formatted with short paragraphs, bold text highlights (using single * asterisks), and a few high-quality emojis.
5. NO PLACEHOLDERS: Final output must contain absolutely NO brackets, no [Your Name], no [Insert Link], etc. Output must be 100% ready to copy-paste.
"""
        else:
            is_broken = int(lead_data.get('is_broken_website', 0)) == 1
            website_url = lead_data.get('website', '')

            if is_broken:
                prompt = f"""
You are an Elite Business Development Consultant, Growth Hacker, and Modern Web Designer in India who helps local businesses double their customers using stunning, fast web portals and digital storefronts.

Write a highly personalized, extremely conversational, and premium sales pitch for the following business whose listed website is BROKEN/DOWN:
- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}
- Website: {website_url} (IT IS BROKEN/DOWN! Standard requests return errors or timeouts. A major credibility leak for a business.)

Best matching project proof to naturally mention:
{project_sample}

TONE DIRECTIVES:
{tone_directives}

LENGTH & STRUCTURE DIRECTIVES:
{length_directives}

SMART HOOK DIRECTIVES:
{hook_type_directive}

CRITICAL COPYWRITING DIRECTIVES FOR BROKEN WEBSITES (FOLLOW THOROUGHLY):
1. CASUAL GREETING: NEVER start with robotic or formal things like "नमस्ते {lead_data.get('name')} Team! 👋" or "प्रिय S Salon". Instead, use extremely natural, friendly greetings like "Hey {lead_data.get('name')} team! 👋" or "Hey there! Quick question for the team at {lead_data.get('name')}."
2. IMPRESSION OVER FLATTERY & BROKEN WEBSITE HOOK: Say something exciting and real about their reviews first, then immediately flag the broken website listed.
   For example:
   "Google par aapke *{lead_data.get('rating')} rating* aur *{lead_data.get('reviews')} reviews* dekhe—sach mein kamaal ka response hai! Par maine ek critical issue notice kiya... Google Maps par aapki listed website ({website_url}) open nahi ho rahi hai (down/broken error dikha rahi hai). ⚠️"
3. THE GAP (CONVERSATIONAL PAIN POINT): Explain that when high-paying clients click the website and see an error/blank page, it immediately kills trust. They think the business has shut down or is unprofessional, causing them to lose premium clients to competitors. We can easily fix this and get it up.
4. THE SOCIAL PROOF: Incorporate the provided portfolio work sample sentence naturally. The portfolio sample is already a complete, conversational sentence describing our work (e.g., "maine haal hi mein ek GYM website banayi hai..."). Simply integrate it smoothly as its own short paragraph, or weave it in with a simple transition.
   E.g., "{project_sample}"
5. HIGH-VALUE CALL TO ACTION (CTA): Make the offer absolutely irresistible. Instead of asking for a boring call, offer a free homepage mockup draft styled perfectly for them to replace their broken site!
   E.g., "Maine aapki website ko bypass karke ek naya *premium, fast-loading homepage mockup / raw design layout* sketch kiya hai. Kya main uska ek quick link ya screen recording video yahan share karu? Let me know if that sounds good."
6. FORMATTING:
   - Language must be ultra-premium, modern, natural Hinglish (how young entrepreneurs talk on WhatsApp).
   - Use bold text for key numbers and phrases using asterisks (e.g., *4.8 rating*, *broken website*, *free mockup design*).
   - Keep emojis limited to 3 or 4 maximum (e.g. 👋, ⚠️, 🔥, 💬). No emoji spam.
   - NO PLACEHOLDERS: Final output must contain absolutely NO brackets, no [Your Name], no [Insert Link], etc. Output must be 100% ready to copy-paste.
{signoff_directive}
"""
            else:
                prompt = f"""
You are an Elite Business Development Consultant, Growth Hacker, and Modern Web Designer in India who helps local businesses double their customers using stunning, fast web portals and digital storefronts.

Write a highly personalized, extremely conversational, and premium sales pitch for the following business:
- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}
- Website: They DO NOT have a website yet (Huge gap!).

Best matching project proof to naturally mention:
{project_sample}

TONE DIRECTIVES:
{tone_directives}

LENGTH & STRUCTURE DIRECTIVES:
{length_directives}

SMART HOOK DIRECTIVES:
{hook_type_directive}

CRITICAL COPYWRITING DIRECTIVES (FOLLOW THOROUGHLY):
1. CASUAL GREETING: NEVER start with robotic or formal things like "नमस्ते {lead_data.get('name')} Team! 👋" or "प्रिय S Salon". Instead, use extremely natural, friendly greetings like "Hey {lead_data.get('name')} team! 👋" or "Hey there! Quick question for the team at {lead_data.get('name')}."
2. IMPRESSION OVER FLATTERY: Do NOT write generic praise like "Aapka review dekh kar mujhe bahut khushi hui." That sounds fake and robotic. Instead, say something exciting and real like:
   "Google par aapke *{lead_data.get('rating')} rating* aur *{lead_data.get('reviews')} reviews* dekhe—sach mein kamaal ka response hai! {lead_data.get('city', 'your city')} mein log aapki service ko sach mein bahut pasand kar rahe hain. 🔥"
3. THE GAP (CONVERSATIONAL PAIN POINT): Pivot smoothly. Explain that when high-paying clients look for the best salons/services in their area, they expect an interactive digital booking experience or digital gallery, and not having a website means losing premium clients.
4. THE SOCIAL PROOF: Incorporate the provided portfolio work sample sentence naturally. The portfolio sample is already a complete, conversational sentence describing our work (e.g., "maine haal hi mein ek GYM website banayi hai..."). Simply integrate it smoothly as its own short paragraph, or weave it in with a simple transition.
   E.g., "{project_sample}"
5. HIGH-VALUE CALL TO ACTION (CTA): Make the offer absolutely irresistible and low-friction. Instead of asking for a boring call, offer a free draft/mockup!
   E.g., "Maine aapke business details ke sath ek *chota sa premium homepage mockup / raw design layout* sketch kiya hai. Kya main uska ek quick link ya screen recording video yahan share karu? Let me know if that sounds good."
6. FORMATTING:
   - Language must be ultra-premium, modern, natural Hinglish (how young entrepreneurs talk on WhatsApp).
   - Use bold text for key numbers and phrases using asterisks (e.g., *4.8 rating*, *70%+ premium customers*, *free mockup design*).
   - Keep emojis limited to 3 or 4 maximum (e.g. 👋, 🔥, 📈, 💬). No emoji spam.
   - NO PLACEHOLDERS: Final output must contain absolutely NO brackets, no [Your Name], no [Insert Link], etc. Output must be 100% ready to copy-paste.
{signoff_directive}
"""

        # 1. Quick validation: Google API Keys ALWAYS start with "AIza"
        if not api_key.startswith("AIza"):
            raise Exception("Invalid Gemini API Key format. Google API keys must start with 'AIza' (e.g. 'AIzaSy...'). Please make sure you copied the correct key from Google AI Studio and did not paste your SerpApi key here.")

        # 2. Dynamic Model Discovery: Ask Google what models this key supports!
        discovered_models = []
        try:
            print("Querying Google for available models...")
            list_url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
            res = requests.get(list_url, timeout=10)
            
            if res.status_code == 200:
                models_data = res.json().get("models", [])
                for m in models_data:
                    name = m.get("name", "")
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        # Extract short name (e.g. "models/gemini-1.5-flash" -> "gemini-1.5-flash")
                        model_id = name.split("/")[-1] if "/" in name else name
                        discovered_models.append(("v1", model_id))
                print(f"Dynamically discovered models: {discovered_models}")
        except Exception as list_err:
            print(f"Model discovery query failed: {list_err}. Falling back to default list.")

        # 3. Compile final models list to try (discovered models first, then hardcoded fallbacks)
        models_to_try = discovered_models + [
            ("v1", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-flash-latest"),
            ("v1", "gemini-1.5-pro"),
            ("v1beta", "gemini-pro")
        ]

        # Remove duplicates while preserving order
        seen = set()
        final_models = []
        for ver, mod in models_to_try:
            if (ver, mod) not in seen:
                seen.add((ver, mod))
                final_models.append((ver, mod))

        last_error = ""
        for version, model in final_models:
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
                except Exception:
                    last_error = f"Status {response.status_code}"
                print(f"Model {model} on {version} failed: {last_error}")
                
            except requests.exceptions.Timeout:
                last_error = "Request timed out."
                print(f"Model {model} timed out.")
            except Exception as e:
                last_error = str(e)
                print(f"Network error with model {model}: {last_error}")

        # Check if the error is the common Google Cloud "API not enabled" or "Not found/supported" issue
        if "not found for API version" in last_error or "not supported for generateContent" in last_error:
            raise Exception(
                "Your API key is a valid Google Cloud key, but the Gemini API (Generative Language API) "
                "is not enabled or is restricted for this key.\n\n"
                "To fix this, please do ONE of the following:\n"
                "1. [RECOMMENDED] Go to Google AI Studio (https://aistudio.google.com/), click 'Get API key', and create a new key. Keys created in AI Studio have Gemini enabled automatically.\n"
                "2. If you created this key in the Google Cloud Console: Go to your Google Cloud Console project, search for the 'Generative Language API' in the API Library, and click 'Enable'. Also, ensure that any API restrictions on your API key under 'Credentials' allow the 'Generative Language API'."
            )

        raise Exception(f"All Gemini models failed. Last error: {last_error}")
