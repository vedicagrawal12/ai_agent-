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
        previous_pitch: str = None,
        mockup_link: str = ""
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
- PERSONA: A super friendly, enthusiastic local freelance developer in India who is passionate about helping local brands look elite online.
- TONE: Casual, extremely warm, helpful, very human. Talk like a friendly tech-savvy partner in colloquial Hinglish.
- VALUE ADD: Appreciates their business's popularity naturally. NEVER sound like a corporate agency, heavy salesperson, or robot. Keep it very conversational.
- CTA: Offers a super friendly, zero-pressure preview mockup link designed specifically for them to check out.
"""
        elif tone == "direct":
            tone_directives = """
- PERSONA: A sharp, growth-minded local digital growth consultant.
- TONE: Direct, professional, growth-focused, metric-conscious, but polite and conversational. Speaks natural, founder-to-founder Hinglish.
- VALUE ADD: Cleanly highlights customer booking leaks and digital trust gaps.
- CTA: Offers a quick look at a raw digital storefront layout draft, zero commitments.
"""
        else: # elite
            tone_directives = """
- PERSONA: Elite Business Development Consultant & Modern Web Strategy Expert.
- TONE: Professional, warm, polished, growth-focused, authoritative yet super friendly. Ditch textbook formal terms. Speak like a premium digital partner.
- VALUE ADD: Appreciates their massive local reputation and highlights how a top-tier digital experience matches their real-world quality.
- CTA: Offers to share a premium custom-sketched homepage raw mockup/draft layout for their brand.
"""

        # Resolve length directives
        length_directives = ""
        if length == "short":
            length_directives = """
- LENGTH: Brief, snappy, and DM-friendly (maximum 2-3 very short sentences/paragraphs, under 90 words total).
- STRUCTURE: Casual hook, drop the digital gap, state the matched portfolio proof sentence naturally, and give the CTA. Keep it compact so they can see it instantly on mobile.
"""
        else: # detailed
            length_directives = """
- LENGTH: Detailed and structured (3-4 crisp, mobile-friendly paragraphs, under 170 words total).
- STRUCTURE: Beautiful natural flow starting with a warm casual hook, highlighting the trust/conversion gap logically, presenting the matched work sample, and concluding with a friendly mockup draft offer.
"""

        # Resolve smart review count hooks
        try:
            reviews_count = int(lead_data.get('reviews', 0))
        except (ValueError, TypeError):
            reviews_count = 0
        
        if reviews_count >= 100:
            hook_type_directive = f"""
- SMART HOOK (ESTABLISHED AUTHORITY): This local business has a massive review count ({reviews_count} reviews) and is clearly an established local favorite. Frame the pitch around scaling, keeping up with demand, and retaining premium customers who prefer quick booking interfaces. (e.g. 'Aap Bhopal ke elite brands mein aate hain...' or 'Google par aapka setup dekh kar maza aa gaya!').
"""
        else:
            hook_type_directive = f"""
- SMART HOOK (TRUST & CREDIBILITY BUILDER): This business is growing and has a good start ({reviews_count} reviews). Frame the pitch around building massive trust, credibility, first impression power, and turning online searchers into lifetime customers in {lead_data.get('city', 'your city')} using a professional digital storefront.
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
            signoff_directive = f"\n7. SIGN OFF: Sign off the message naturally as '{signoff_str}' (e.g. 'Best, {name}' or similar, keeping it friendly and casual)."
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
You are an Elite B2B Growth Strategist, Freelance Web Developer, and Conversion Consultant in India. You write highly personalized, warm, and 100% human-sounding WhatsApp pitches for local business owners.
Write an outreach pitch for a local business whose website is BROKEN/DOWN (it returns errors/fails to load, causing them to lose premium clients):

- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}
- Listed Broken Website: {website_url}

Dynamic live draft mockup link built specifically for them (if provided, weave it naturally as the primary CTA, otherwise ask if you can share one):
{mockup_link}

Best matching project proof to naturally mention:
{project_sample}

TONE DIRECTIVES:
{tone_directives}

LENGTH & STRUCTURE DIRECTIVES:
{length_directives}

SMART HOOK DIRECTIVES:
{hook_type_directive}

CRITICAL COPYWRITING DIRECTIVES FOR BROKEN WEBSITES (FOLLOW THOROUGHLY):
1. CASUAL GREETING: NEVER start with formal, robotic things like "नमस्ते {lead_data.get('name')} Team! 👋" or "प्रिय S Salon". Instead, use extremely natural, friendly, human greetings like "Hey {lead_data.get('name')} team! 👋" or "Hey there! Quick question for the team at {lead_data.get('name')}."
2. IMPRESSION OVER FLATTERY & BROKEN WEBSITE HOOK: Speak like a real human who just noticed a bug. Start with a direct, casual statement about their amazing local reputation, then bring up the broken website naturally. Do NOT repeat a single static script. Vary your style.
   For example:
   "Hey there! Bhopal me aapka setup sach me bahut popular hai—Google par aapke *{lead_data.get('rating')} rating* aur *{lead_data.get('reviews')} reviews* dekh kar maza aa gaya! 🔥 Par maine ek critical issue notice kiya... Google Maps par aapki listed website open nahi ho rahi hai (error page/down dikha rahi hai). ⚠️"
   (Note: Do NOT write or print the actual raw broken website URL '{website_url}' in the output text itself to avoid triggering safety/phishing link filters).
3. THE CONVERSATIONAL PAIN POINT (THE GAP): Explain in casual Hinglish how this is a massive trust leak. When premium clients search for the best salons/services in their area, they click the website first. If it shows an error, they think the business has shut down or is unmanaged, and immediately switch to a competitor.
4. THE SOCIAL PROOF: Incorporate the provided portfolio work sample sentence naturally. Connect it smoothly into the conversation. The portfolio sample is already a complete, conversational sentence describing our work (e.g., "maine haal hi mein ek GYM website banayi hai..."). Simply integrate it smoothly as its own short paragraph, or weave it in with a simple transition.
   E.g., "{project_sample}"
5. HIGH-VALUE CALL TO ACTION (CTA): Make the offer absolutely irresistible. Instead of asking for a boring call, offer a free homepage mockup draft styled perfectly for them!
   - IF the mockup link is provided above (i.e. "{mockup_link}" is not empty), you MUST naturally weave this link into your CTA (e.g., "Maine aapki website ko bypass karke ek premium live *homepage mockup layout* sketch kiya hai, aap is link par check kar sakte hain: {mockup_link} ...").
   - IF the mockup link is not provided, ask to share (e.g. "Maine aapki website ko bypass karke ek naya *homepage mockup layout* sketch kiya hai. Kya main uska ek quick link ya screen recording video yahan share karu? Let me know if that sounds good.").
6. FORMATTING & LANGUAGE STYLE (CRITICAL FOR HUMAN FEEL):
   - LANGUAGE: Must be highly natural, conversational Hinglish (how modern young founders and entrepreneurs talk on WhatsApp in India). Ditch textbook formal vocabulary. Use words like: *setup*, *vibe*, *fuss*, *traffic*, *leads*, *look*, *draft*, *leakage*, *switch*.
   - Keep paragraphs short (maximum 2-3 sentences per paragraph) with clean spacing to look great on WhatsApp mobile screens.
   - Use bold text for key numbers and phrases using asterisks (e.g., *{lead_data.get('rating')} rating*, *website down*, *free mockup design*).
   - EMOJIS: Keep emojis limited to 3 or 4 maximum (e.g. 👋, ⚠️, 🔥, 📈). Do NOT spam emojis at the end of every sentence.
   - NO PLACEHOLDERS: Final output must contain absolutely NO brackets, no [Your Name], no [Insert Link], etc. Output must be 100% ready to copy-paste.
{signoff_directive}
"""
            else:
                prompt = f"""
You are an Elite B2B Growth Strategist, Freelance Web Developer, and Conversion Consultant in India. You write highly personalized, warm, and 100% human-sounding WhatsApp pitches for local business owners.
Write an outreach pitch for a local business who DOES NOT HAVE A WEBSITE YET:

- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}

Dynamic live draft mockup link built specifically for them (if provided, weave it naturally as the primary CTA, otherwise ask if you can share one):
{mockup_link}

Best matching project proof to naturally mention:
{project_sample}

TONE DIRECTIVES:
{tone_directives}

LENGTH & STRUCTURE DIRECTIVES:
{length_directives}

SMART HOOK DIRECTIVES:
{hook_type_directive}

CRITICAL COPYWRITING DIRECTIVES (FOLLOW THOROUGHLY):
1. CASUAL GREETING: NEVER start with formal, robotic things like "नमस्ते {lead_data.get('name')} Team! 👋" or "प्रिय S Salon". Instead, use extremely natural, friendly, human greetings like "Hey {lead_data.get('name')} team! 👋" or "Hey there! Quick question for the team at {lead_data.get('name')}."
2. IMPRESSION OVER FLATTERY: Speak like a real human salesperson who is genuinely impressed. Do NOT repeat a single static script. Vary your style.
   For example:
   "Hey there! Bhopal me aapka setup sach me bahut popular hai—Google par aapke *{lead_data.get('rating')} rating* aur *{lead_data.get('reviews')} reviews* dekh kar maza aa gaya! 🔥 Bhopal ke log aapki services ko sach me bahut pasand karte hain."
3. THE GAP (CONVERSATIONAL PAIN POINT): Pivot smoothly. Explain in conversational Hinglish that today, premium clients look for a modern, sleek digital booking experience or online booking portal. Not having a website is a huge missed opportunity to capture and automate high-paying memberships/bookings.
4. THE SOCIAL PROOF: Incorporate the provided portfolio work sample sentence naturally. Connect it smoothly into the conversation. The portfolio sample is already a complete, conversational sentence describing our work (e.g., "maine haal hi mein ek GYM website banayi hai..."). Simply integrate it smoothly as its own short paragraph, or weave it in with a simple transition.
   E.g., "{project_sample}"
5. HIGH-VALUE CALL TO ACTION (CTA): Make the offer absolutely irresistible and low-friction. Instead of asking for a boring call, offer a free draft/mockup!
   - IF the mockup link is provided above (i.e. "{mockup_link}" is not empty), you MUST naturally weave this link into your CTA (e.g., "Maine aapke business details ke sath ek premium live *homepage mockup layout* sketch kiya hai, aap is link par check kar sakte hain: {mockup_link} ...").
   - IF the mockup link is not provided, ask to share (e.g. "Maine aapke business details ke sath ek *chota sa premium homepage mockup / raw design layout* sketch kiya hai. Kya main uska ek quick link ya screen recording video yahan share karu? Let me know if that sounds good.").
6. FORMATTING & LANGUAGE STYLE (CRITICAL FOR HUMAN FEEL):
   - LANGUAGE: Must be highly natural, conversational Hinglish (how modern young founders and entrepreneurs talk on WhatsApp in India). Ditch textbook formal vocabulary. Use words like: *setup*, *vibe*, *fuss*, *traffic*, *leads*, *look*, *draft*, *leakage*, *switch*.
   - Keep paragraphs short (maximum 2-3 sentences per paragraph) with clean spacing to look great on WhatsApp mobile screens.
   - Use bold text for key numbers and phrases using asterisks (e.g., *{lead_data.get('rating')} rating*, *leads*, *free mockup design*).
   - EMOJIS: Keep emojis limited to 3 or 4 maximum (e.g. 👋, 🔥, 📈, 💬). Do NOT spam emojis at the end of every sentence.
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
