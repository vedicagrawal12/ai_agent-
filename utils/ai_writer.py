import requests
import json
import time

class AIOutreachWriter:
    @staticmethod
    def generate_pitch(
        lead_data: dict, 
        project_sample: str, 
        api_key: str,
        tone: str = "elite",
        length: str = "detailed",
        service: str = "web_design",
        sender_info: dict = None,
        refine_feedback: str = None,
        previous_pitch: str = None,
        mockup_link: str = "",
        custom_pitch_rules: str = "",
        min_words: int = 150
    ) -> str:
        """
        Generates a highly personalized, human-like sales pitch using the Gemini API.
        Uses raw requests to avoid installing extra dependencies.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        custom_rules_directive = ""
        if custom_pitch_rules:
            custom_rules_directive = f"\n- CUSTOM USER PROFILE & OUTREACH RULES (CRITICAL: You must strictly incorporate these personalized preferences and details in your pitch writing):\n{custom_pitch_rules}\n"

        # Resolve persona and service directives based on target service (BUG-L3)
        persona_directive, service_directives = AIOutreachWriter._resolve_service_directives(service)

        # Resolve tone directives
        tone_directives = ""
        if tone == "friendly":
            tone_directives = f"""
- PERSONA: A super friendly, enthusiastic local {persona_directive} in India who is passionate about helping local brands look elite online.
- TONE: Casual, extremely warm, helpful, very human. Talk like a friendly partner in colloquial Hinglish.
- VALUE ADD: Appreciates their business's popularity naturally. NEVER sound like a corporate agency, heavy salesperson, or robot. Keep it very conversational.
- CTA: Offers a super friendly, zero-pressure preview mockup/draft layout designed specifically for them to check out.
"""
        elif tone == "direct":
            tone_directives = f"""
- PERSONA: A sharp, growth-minded local {persona_directive} in India.
- TONE: Direct, professional, growth-focused, metric-conscious, but polite and conversational. Speaks natural, founder-to-founder Hinglish.
- VALUE ADD: Cleanly highlights customer booking leaks and digital presence trust gaps.
- CTA: Offers a quick look at a raw digital draft layout, zero commitments.
"""
        else: # elite
            tone_directives = f"""
- PERSONA: Elite {persona_directive} & Modern Brand Strategy Expert.
- TONE: Professional, warm, polished, growth-focused, authoritative yet super friendly. Ditch textbook formal terms. Speak like a premium digital partner.
- VALUE ADD: Appreciates their massive local reputation and highlights how a top-tier digital experience matches their real-world quality.
- CTA: Offers to share a premium custom-sketched homepage or growth layout raw mockup/draft for their brand.
"""

        # Resolve length directives based on min_words and length profile
        if length == "short":
            if min_words >= 350:
                length_directives = f"""
- LENGTH: Detailed and structured (minimum {min_words} words, structured inside 4-6 paragraphs).
- STRUCTURE: Hook appreciating reviews/rating, Digital Gap/Leak analysis, Solution & Social Proof (mentioning {project_sample}), 3-step action roadmap, and a clean call to action (mockup link).
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words. Expand on all sections, including specific examples, to ensure you meet this target. Avoid summarizing.
"""
            elif min_words >= 250:
                length_directives = f"""
- LENGTH: Medium-length and structured (minimum {min_words} words, structured inside 3-4 paragraphs).
- STRUCTURE: Casual hook, Digital Gap/Leak analysis, Solution & Social Proof (mentioning {project_sample}), and call to action.
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words. Elaborate on details to meet this length naturally.
"""
            else:
                length_directives = f"""
- LENGTH: Brief, snappy, and DM-friendly (minimum {min_words} words, structured inside 2-3 short paragraphs).
- STRUCTURE: Casual hook, drop the digital gap, state the matched portfolio proof sentence naturally, and give the CTA.
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words.
"""
        else: # detailed
            if min_words >= 450:
                length_directives = f"""
- LENGTH: Comprehensive, highly detailed, and exhaustive (minimum {min_words} words, structured inside 5-8 fully-developed paragraphs).
- STRUCTURE:
  1. WARM CASUAL HOOK: Appreciate their amazing local reputation, specifically referencing their Google reviews ({lead_data.get('reviews')}) and rating ({lead_data.get('rating')}).
  2. DETAILED DIGITAL AUDIT / LEAK POINT: Explain why lacking this service (e.g. {service}) causes severe client loss or search ranking drop. Break down the psychology of local customers choosing competitors with active digital setups.
  3. COMPREHENSIVE SOLUTION & VALUE PROPOSITION: Detail the custom strategy you will deploy. Explain how the matched project proof ({project_sample}) solved this exact issue (e.g., doubling bookings or conversions).
  4. STEP-BY-STEP SERVICE ROADMAP: Outline a 3-4 step plan (e.g., Step 1: Interface Wireframing, Step 2: Local SEO Alignment, Step 3: Call-to-Action Optimization).
  5. ROI & BUSINESS OUTLOOK: Detail the business return (increased reviews, automated scheduling, higher search prominence).
  6. CALL TO ACTION (CTA): Make a low-friction mockup draft offer.
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words. Do NOT truncate or summarize. Expand each paragraph with deep insights, specific examples, local context, and marketing value to meet this length naturally.
"""
            elif min_words >= 350:
                length_directives = f"""
- LENGTH: Deeply detailed and structured (minimum {min_words} words, structured inside 4-6 fully-developed paragraphs).
- STRUCTURE:
  1. Warm hook appreciating their reviews/rating.
  2. In-depth Digital Gap analysis explaining why their current state leaks premium customers.
  3. Tailored Solution highlighting the matched portfolio proof ({project_sample}).
  4. 3-step action roadmap to address the gap.
  5. Low-friction mockup draft offer CTA.
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words. Write full, descriptive paragraphs rather than short summaries to hit this target.
"""
            elif min_words >= 250:
                length_directives = f"""
- LENGTH: Detailed and structured (minimum {min_words} words, structured inside 4-5 paragraphs).
- STRUCTURE:
  1. Warm hook appreciating rating/reviews.
  2. Digital gap description (leaks, competitors).
  3. Custom solution and portfolio matching.
  4. Mockup layout draft offer.
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words. Elaborate on details to meet this length naturally.
"""
            else:
                length_directives = f"""
- LENGTH: Detailed (minimum {min_words} words, structured inside 3-4 paragraphs).
- STRUCTURE: Beautiful natural flow starting with a warm casual hook, highlighting the trust/conversion gap logically, presenting the matched work sample, and concluding with a friendly mockup draft offer.
- WORD COUNT REQUIREMENT (CRITICAL): The generated pitch must strictly be at least {min_words} words.
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
- SMART HOOK (TRUST & CREDIBILITY BUILDER): This business is growing and has a good start ({reviews_count} reviews). Frame the pitch around building massive trust, credibility, first impression power, and turning online searchers into lifetime customers in {lead_data.get('city', 'your city')} using a professional digital presence.
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
{custom_rules_directive}
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
You are an Elite B2B Growth Strategist, {persona_directive} in India. You write highly personalized, warm, and 100% human-sounding WhatsApp pitches for local business owners.
Write an outreach pitch for a local business whose website is BROKEN/DOWN (it returns errors/fails to load, causing them to lose premium clients):

- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}
- Listed Broken Website: {website_url}
{custom_rules_directive}
Dynamic live draft mockup link built specifically for them (if provided, weave it naturally as the primary CTA, otherwise ask if you can share one):
{mockup_link}

Best matching project proof to naturally mention:
{project_sample}

SERVICE CONFIGURATION:
{service_directives}

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
3. THE CONVERSATIONAL PAIN POINT (THE GAP): Explain in casual Hinglish how this website breakdown is a massive trust leak. Connect it directly to the service you are pitching:
   - If Web Design: Losing customers to competitors due to a broken site.
   - If SEO/GMB: Broken site harms search ranking and authority, causing them to slip from search results.
   - If Social Media: Traffic from pages is wasted because the landing link is broken.
4. THE SOCIAL PROOF: Incorporate the provided portfolio work sample sentence naturally.
5. HIGH-VALUE CALL TO ACTION (CTA): Make the offer absolutely irresistible. Offer a custom mockup layout or draft structure. If mockup link is provided ({mockup_link}), you MUST naturally weave this link into your CTA.
6. FORMATTING & LANGUAGE STYLE (CRITICAL FOR HUMAN FEEL):
   - LANGUAGE: Must be highly natural, conversational Hinglish. Use words like: *setup*, *vibe*, *fuss*, *traffic*, *leads*, *look*, *draft*, *leakage*, *switch*.
   - Keep paragraphs short (maximum 2-3 sentences per paragraph) with clean spacing.
   - Use bold text for key numbers and phrases using asterisks.
   - EMOJIS: Keep emojis limited to 3 or 4 maximum.
   - NO PLACEHOLDERS: Final output must contain absolutely NO brackets, no [Your Name], no [Insert Link], etc.
7. PITCH OBJECTIVE: You must strictly align your pitch with the provided SERVICE TO PITCH and VALUE PROPOSITION guidelines under SERVICE CONFIGURATION. Pitch the selected service (SEO, SMM, GMB, or Web Design) instead of defaulting only to web design.
{signoff_directive}
"""
            else:
                prompt = f"""
You are an Elite B2B Growth Strategist, {persona_directive} in India. You write highly personalized, warm, and 100% human-sounding WhatsApp pitches for local business owners.
Write an outreach pitch for a local business who DOES NOT HAVE A WEBSITE YET:

- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}
{custom_rules_directive}
Dynamic live draft mockup link built specifically for them (if provided, weave it naturally as the primary CTA, otherwise ask if you can share one):
{mockup_link}

Best matching project proof to naturally mention:
{project_sample}

SERVICE CONFIGURATION:
{service_directives}

TONE DIRECTIVES:
{tone_directives}

LENGTH & STRUCTURE DIRECTIVES:
{length_directives}

SMART HOOK DIRECTIVES:
{hook_type_directive}

CRITICAL COPYWRITING DIRECTIVES (FOLLOW THOROUGHLY):
1. CASUAL GREETING: NEVER start with formal, robotic things like "नमस्ते {lead_data.get('name')} Team! 👋" or "प्रिय S Salon". Instead, use extremely natural, friendly, human greetings like "Hey {lead_data.get('name')} team! 👋" or "Hey there! Quick question for the team at {lead_data.get('name')}."
2. IMPRESSION OVER FLATTERY: Speak like a real human salesperson who is genuinely impressed. Do NOT repeat a single static script. Vary your style.
3. THE GAP (CONVERSATIONAL PAIN POINT): Pivot smoothly. Explain in conversational Hinglish that today, local customers check online to discover their services. Connect the gap to the service you are pitching:
   - If Web Design: Not having a website is a huge missed opportunity to capture and automate high-paying memberships/bookings.
   - If SEO/GMB: Missing out on massive organic search queries and calls from customers in their city.
   - If Social Media: Lacking a visually stunning active visual brand feed on Instagram where new clients search.
4. THE SOCIAL PROOF: Incorporate the provided portfolio work sample sentence naturally.
5. HIGH-VALUE CALL TO ACTION (CTA): Make the offer absolutely irresistible and low-friction. Offer a custom mockup layout or draft strategy. If mockup link is provided ({mockup_link}), you MUST naturally weave this link into your CTA.
6. FORMATTING & LANGUAGE STYLE (CRITICAL FOR HUMAN FEEL):
   - LANGUAGE: Must be highly natural, conversational Hinglish.
   - Keep paragraphs short (maximum 2-3 sentences per paragraph).
   - Use bold text for key numbers and phrases using asterisks.
   - EMOJIS: Keep emojis limited to 3 or 4 maximum.
   - NO PLACEHOLDERS: Final output must contain absolutely NO brackets, no [Your Name], no [Insert Link], etc.
7. PITCH OBJECTIVE: You must strictly align your pitch with the provided SERVICE TO PITCH and VALUE PROPOSITION guidelines under SERVICE CONFIGURATION. Pitch the selected service (SEO, SMM, GMB, or Web Design) instead of defaulting only to web design.
{signoff_directive}
"""

        return AIOutreachWriter._call_gemini_api(prompt, api_key)

    @staticmethod
    def generate_email_pitch(
        lead_data: dict, 
        project_sample: str, 
        api_key: str,
        tone: str = "elite",
        service: str = "web_design",
        sender_info: dict = None,
        mockup_link: str = "",
        custom_pitch_rules: str = "",
        min_words: int = 150
    ) -> str:
        """
        Generates a highly personalized, human-like sales cold email with a Subject Line and Body.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        custom_rules_directive = ""
        if custom_pitch_rules:
            custom_rules_directive = f"\n- CUSTOM USER PROFILE & OUTREACH RULES (CRITICAL: You must strictly incorporate these personalized preferences and details in your pitch writing):\n{custom_pitch_rules}\n"

        # Resolve persona and service directives based on target service (BUG-L3)
        persona_directive, service_directives = AIOutreachWriter._resolve_service_directives(service)

        # Resolve tone directives
        tone_directives = ""
        if tone == "friendly":
            tone_directives = f"""
- PERSONA: A super friendly, enthusiastic local {persona_directive} in India who loves building gorgeous client setups.
- TONE: Warm, extremely conversational, casual, very helpful. Speak like an excited partner in natural Hinglish.
- VALUE ADD: Focus on helping them stand out and look extremely good. Avoid aggressive hard-selling.
"""
        elif tone == "direct":
            tone_directives = f"""
- PERSONA: A sharp, growth-minded local {persona_directive} in India.
- TONE: Professional, casual but direct, value-heavy, metric-conscious. Speak founder-to-founder Hinglish.
- VALUE ADD: Highlight booking/appointment leaks, customer conversions, and the credibility lost from not optimizing their online presence.
"""
        else: # elite
            tone_directives = f"""
- PERSONA: Elite {persona_directive} & Modern Brand Strategy Expert.
- TONE: Elite, polished, warm, growth-focused, highly professional yet super friendly.
- VALUE ADD: Contrast their amazing real-world popularity (Google reviews count) with their missed online capability to capture and automate client bookings.
"""

        # Resolve smart reviews count hook
        try:
            reviews_count = int(lead_data.get('reviews', 0))
        except (ValueError, TypeError):
            reviews_count = 0
            
        is_broken = int(lead_data.get('is_broken_website', 0)) == 1
        website_url = lead_data.get('website', '')

        # Resolve sender profile sign-off
        name = sender_info.get("name", "").strip() if sender_info else ""
        brand = sender_info.get("brand", "").strip() if sender_info else ""
        role = sender_info.get("role", "").strip() if sender_info else ""
        
        signoff_parts = []
        if name:
            signoff_parts.append(name)
        if role:
            signoff_parts.append(f"({role})")
        if brand:
            signoff_parts.append(f"at {brand}")
        
        signoff_str = " ".join(signoff_parts) if signoff_parts else "Your B2B Growth Partner"

        # Resolve email length directives based on min_words
        if min_words >= 450:
            email_length_directives = f"""
- LENGTH: Comprehensive, highly detailed, and exhaustive (minimum {min_words} words, structured inside 5-8 fully-developed paragraphs in the email body).
- STRUCTURE:
  1. Warm, casual, founder-to-founder human greeting.
  2. HOOK: Respectful appreciation of their local setup in {lead_data.get('city')}, citing rating and reviews.
  3. COMPREHENSIVE OUTSIDE AUDIT / TRUST LEAK: In-depth analysis of what they are missing (e.g. no conversion funnel, broken layout, local SEO drop-off) and the business cost.
  4. TAILORED SOLUTION & PORTFOLIO: Detail the solution and explain the matched case study ({project_sample}) showing tangible results.
  5. STRATEGIC ROADMAP: Provide a 3-4 step implementation blueprint of how you will deploy {service}.
  6. ROI EXPECTATION: Explain the direct impact on their bottom line (e.g., more direct bookings, higher Google Maps ranking).
  7. CTA: Offer to share the custom mockup or live draft preview ({mockup_link}).
  8. Professional sign-off.
- WORD COUNT REQUIREMENT (CRITICAL): The generated email body must strictly be at least {min_words} words. Do NOT summarize or use placeholder text. Write rich, descriptive, and value-packed paragraphs to meet this target.
"""
        elif min_words >= 350:
            email_length_directives = f"""
- LENGTH: Detailed and comprehensive (minimum {min_words} words, structured inside 4-6 fully-developed paragraphs in the email body).
- STRUCTURE:
  1. Casual founder-to-founder greeting.
  2. Hook appreciating reviews/rating.
  3. Digital gap analysis (leaks, credibility drop).
  4. Solution incorporating matched portfolio proof ({project_sample}).
  5. 3-step action roadmap.
  6. CTA offering mockup/draft preview ({mockup_link}).
  7. Professional sign-off.
- WORD COUNT REQUIREMENT (CRITICAL): The generated email body must strictly be at least {min_words} words. Elaborate on details to meet this length naturally.
"""
        elif min_words >= 250:
            email_length_directives = f"""
- LENGTH: Medium-length and structured (minimum {min_words} words, structured inside 4-5 paragraphs in the email body).
- STRUCTURE:
  1. Human greeting.
  2. Hook appreciating reviews/rating.
  3. Digital gap/leak description.
  4. Custom solution and portfolio project.
  5. Mockup layout CTA.
  6. Professional sign-off.
- WORD COUNT REQUIREMENT (CRITICAL): The generated email body must strictly be at least {min_words} words. Elaborate on details to meet this length naturally.
"""
        else:
            email_length_directives = f"""
- LENGTH: Standard cold email (minimum {min_words} words, structured inside 3-4 paragraphs in the email body).
- STRUCTURE:
  1. Human greeting.
  2. Hook appreciating reviews/rating.
  3. Digital gap/leak description.
  4. Custom solution and portfolio project.
  5. Mockup layout CTA.
  6. Professional sign-off.
- WORD COUNT REQUIREMENT (CRITICAL): The generated email body must strictly be at least {min_words} words.
"""

        # Build prompt
        prompt = f"""
You are an Elite B2B Growth Strategy Copywriter in India. Your task is to write a highly personalized, warm, and 100% human-sounding B2B Cold Email for a local business to pitch them your custom services.

Here are the details of the business:
- Business Name: {lead_data.get('name', 'Business')}
- Category: {lead_data.get('category', 'Business')}
- Location: {lead_data.get('city', 'your city')}
- Google Maps Rating: {lead_data.get('rating', '0')}
- Google Maps Reviews: {lead_data.get('reviews', '0')}
- Website State: {"Broken/Down listed URL: " + website_url if is_broken else "DOES NOT HAVE A WEBSITE YET"}
{custom_rules_directive}
Best matching project proof to mention in the email body:
{project_sample}

Dynamic live draft mockup link designed specifically for them (if provided, weave it naturally as a key highlight, otherwise offer to make one):
{mockup_link}

SERVICE CONFIGURATION:
{service_directives}

TONE DIRECTIVES:
{tone_directives}

LENGTH & STRUCTURE DIRECTIVES:
{email_length_directives}

Strict Copywriting Guidelines for Cold Email:
1. SUBJECT LINE: Write a short, highly curiosity-driven, and personalized subject line under 7 words. Never use spammy clickbait or all caps. It should feel like a genuine observation and align with the service (e.g. for SEO: "Question about {lead_data.get('name')}'s search visibility" or for GMB: "Google Maps optimization for {lead_data.get('name')}" or for Web Design: "Quick design layout for {lead_data.get('name')} setup").
2. STRUCTURE: 
   - Follow the structure described in LENGTH & STRUCTURE DIRECTIVES strictly. Ensure every section outlined is fully expanded into its own paragraph.
3. LANGUAGE: Natural conversational Hinglish/English. Speak like a real human partner.
4. SIGN OFF: Use "Best," or "Warm regards," followed by "{signoff_str}".
5. FORMATTING: You MUST separate the Subject Line and the Body cleanly using the exact identifiers "SUBJECT:" and "BODY:". Do not put any formatting tags like markdown in the SUBJECT line. Keep the body in short, clean paragraphs. No placeholders or brackets anywhere!
6. PITCH OBJECTIVE: You must strictly align your pitch with the provided SERVICE TO PITCH and VALUE PROPOSITION guidelines under SERVICE CONFIGURATION. Pitch the selected service (SEO, SMM, GMB, or Web Design) instead of defaulting only to web design.
7. WORD COUNT & DETAIL REQUIREMENT (CRITICAL): The generated email body (the content after 'BODY:') must strictly be at least {min_words} words long. To meet this length naturally, you must go into detail about their industry position, how specifically they are missing out on bookings or conversions, the detailed benefits of the pitch, and describe the matching portfolio sample in detail as specified in LENGTH & STRUCTURE DIRECTIVES. Do not write a short/abbreviated email.

OUTPUT FORMAT (YOU MUST FOLLOW THIS EXACTLY):
SUBJECT: [Curiosity-driven Subject Line]
BODY:
[Email Body Paragraphs here]
"""
        return AIOutreachWriter._call_gemini_api(prompt, api_key)

    @staticmethod
    def _call_gemini_api(prompt: str, api_key: str) -> str:
        """Helper method to handle the stateless requests to the Google Gemini API."""
        # 1. Quick validation: Google API Keys start with "AIza" or "AQ."
        if not api_key.startswith("AIza") and not api_key.startswith("AQ."):
            print("WARNING: Gemini API Key does not start with standard 'AIza' or 'AQ.' prefix. Proceeding anyway.")

        # 2. Dynamically tune generation parameters based on prompt complexity
        #    Longer prompts = user wants detailed output = needs more tokens, time, and creativity
        prompt_len = len(prompt)
        if prompt_len > 4000:
            # Large detailed prompt (350-450 word limit requests)
            max_output_tokens = 2048
            temperature = 0.85
            request_timeout = 45
        elif prompt_len > 2500:
            # Medium prompt (250 word limit requests)
            max_output_tokens = 1500
            temperature = 0.8
            request_timeout = 35
        else:
            # Short/standard prompt (150 word limit requests)
            max_output_tokens = 1024
            temperature = 0.75
            request_timeout = 25

        print(f"[AI Writer Config] prompt_len={prompt_len}, maxTokens={max_output_tokens}, temp={temperature}, timeout={request_timeout}s")

        # 3. Dynamic Model Discovery: Ask Google what models this key supports!
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
                        model_id = name.split("/")[-1] if "/" in name else name
                        discovered_models.append(("v1", model_id))
                print(f"Dynamically discovered models: {discovered_models}")
        except Exception as list_err:
            print(f"Model discovery query failed: {list_err}. Falling back to default list.")

        # 4. Compile final models list to try (capped to prevent long timeout chains)
        discovered_capped = discovered_models[:3]
        models_to_try = discovered_capped + [
            ("v1", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-flash-latest"),
            ("v1", "gemini-1.5-pro"),
            ("v1beta", "gemini-pro")
        ]

        seen = set()
        final_models = []
        for ver, mod in models_to_try:
            if (ver, mod) not in seen:
                seen.add((ver, mod))
                final_models.append((ver, mod))
            if len(final_models) >= 5:
                break

        last_error = ""
        primary_error = ""
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
                    "temperature": temperature,
                    "maxOutputTokens": max_output_tokens
                }
            }

            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        print(f"Retrying Gemini model: {model} on {version} (attempt {attempt}/{max_retries})...")
                    else:
                        print(f"Trying Gemini model: {model} on {version}...")
                    
                    response = requests.post(url, headers=headers, json=payload, timeout=request_timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            # Check if the response was truncated by the model
                            finish_reason = candidates[0].get("finishReason", "")
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                word_count = len(text.split())
                                print(f"Success with Gemini model: {model}! Words generated: {word_count}, finishReason: {finish_reason}")
                                if finish_reason == "MAX_TOKENS" and word_count < 100:
                                    # Output was severely truncated, try next model
                                    print(f"Output truncated at MAX_TOKENS with only {word_count} words, trying next model...")
                                    last_error = "Output truncated (MAX_TOKENS)"
                                    break # Break retry loop to try next model
                                return text.strip()
                    
                    try:
                        error_data = response.json()
                        last_error = error_data.get("error", {}).get("message", f"Status {response.status_code}")
                    except Exception:
                        last_error = f"Status {response.status_code}"
                    
                    # Check for invalid API key immediately to avoid misleading fallbacks
                    if "key not valid" in last_error.lower() or "api key not valid" in last_error.lower() or "invalid api key" in last_error.lower():
                        raise Exception("Invalid Gemini API Key. Google API keys must start with 'AIza' or 'AQ.'. Please check your key in Settings.")
                    
                    if not primary_error:
                        primary_error = last_error
                    print(f"Model {model} on {version} failed (status {response.status_code}): {last_error}")
                    
                    # Check if error is retryable (429, 503, 500, or related keywords)
                    is_retryable = (
                        response.status_code in [429, 500, 503] or
                        any(keyword in last_error.lower() for keyword in ["demand", "rate limit", "quota", "overloaded", "resource exhausted", "limit exceeded", "temp", "busy"])
                    )
                    
                    if is_retryable and attempt < max_retries:
                        sleep_time = 2.0 * (attempt + 1)
                        print(f"Retryable error detected. Sleeping for {sleep_time}s before retrying...")
                        time.sleep(sleep_time)
                        continue
                    
                    # If not retryable or max retries reached, try the next model in the fallback queue
                    break
                    
                except requests.exceptions.Timeout:
                    last_error = "Request timed out."
                    if not primary_error:
                        primary_error = last_error
                    print(f"Model {model} timed out after {request_timeout}s.")
                    if attempt < max_retries:
                        sleep_time = 2.0 * (attempt + 1)
                        print(f"Timeout occurred. Sleeping for {sleep_time}s before retrying...")
                        time.sleep(sleep_time)
                        continue
                    break
                except Exception as e:
                    # Re-raise explicit validation/authentication errors immediately
                    if "Invalid Gemini API Key" in str(e):
                        raise e
                    last_error = str(e)
                    if not primary_error:
                        primary_error = last_error
                    print(f"Network error with model {model}: {last_error}")
                    
                    # Network connection failures are also retryable
                    if attempt < max_retries:
                        sleep_time = 2.0 * (attempt + 1)
                        print(f"Connection issue. Sleeping for {sleep_time}s before retrying...")
                        time.sleep(sleep_time)
                        continue
                    break

        error_to_check = primary_error or last_error
        if "not found for API version" in error_to_check or "not supported for generateContent" in error_to_check or "disabled" in error_to_check.lower():
            raise Exception(
                "Your API key is a valid Google Cloud key, but the Gemini API (Generative Language API) "
                "is not enabled or is restricted for this key.\n\n"
                "To fix this, please do ONE of the following:\n"
                "1. [RECOMMENDED] Go to Google AI Studio (https://aistudio.google.com/), click 'Get API key', and create a new key. Keys created in AI Studio have Gemini enabled automatically.\n"
                "2. If you created this key in the Google Cloud Console: Go to your Google Cloud Console project, search for the 'Generative Language API' in the API Library, and click 'Enable'. Also, ensure that any API restrictions on your API key under 'Credentials' allow the 'Generative Language API'."
            )

        raise Exception(f"All Gemini models failed. Last error: {error_to_check}")

    @staticmethod
    def _resolve_service_directives(service: str) -> tuple:
        persona_directive = ""
        service_directives = ""
        
        if service == "seo":
            persona_directive = "Search Engine Optimization (SEO) Specialist & Business Growth Consultant"
            service_directives = """
- SERVICE TO PITCH: Search Engine Optimization (SEO) & Local Google Ranking services.
- VALUE PROPOSITION: Focus on ranking their Google Business Profile and local search visibility. Explain that ranking high on Google Search and Google Maps brings automated organic inquiries, calls, and foot traffic from clients in their area who are actively searching for their service. Highlight that high search ranking is a sustainable asset compared to constant paid ads.
- KEY PHRASE HIGHLIGHTS: "Google ranking", "organic search traffic", "first page of Google", "local customer inquiries", "ranking high on Google Maps".
"""
        elif service == "social_media":
            persona_directive = "Social Media Brand Architect, Content Strategist, and Visual Outreach Expert"
            service_directives = """
- SERVICE TO PITCH: Social Media Management (Instagram, Facebook) & Visual Branding.
- VALUE PROPOSITION: Focus on building a highly active, visually stunning social media presence (posts, reels, stories). Explain that in their business category, modern premium clients check Instagram and Facebook profiles for the "vibe" and credibility before choosing. Consistent posts build trust, capture direct bookings/reservations, and expand local brand awareness.
- KEY PHRASE HIGHLIGHTS: "Instagram presence", "active engagement", "social media vibe", "reels and posts", "DM bookings", "aesthetic local brand".
"""
        elif service == "gmb":
            persona_directive = "Google Business Profile Specialist & Maps Visibility Consultant"
            service_directives = """
- SERVICE TO PITCH: Google Maps / Google Business Profile (GBP/GMB) Optimization.
- VALUE PROPOSITION: Focus on optimizing their business profile listing on Google Maps. Highlight local SEO listing optimization, managing high-quality photos, attracting and responding to positive reviews, cleaning up business hours, and landing inside the coveted Google Maps "Local 3-Pack" section where 80% of local clicks happen.
- KEY PHRASE HIGHLIGHTS: "Google Maps visibility", "local business profile listing", "GBP optimization", "Google 3-pack ranking", "responding to reviews".
"""
        elif service == "web_design":
            persona_directive = "Freelance Web Developer, UI/UX Designer, and Digital Storefront Consultant"
            service_directives = """
- SERVICE TO PITCH: Custom Website Design & Development.
- VALUE PROPOSITION: Focus on building a professional, high-performance, mobile-responsive website, or replacing/fixing their currently down/broken website. Explain that a premium digital storefront builds instant trust, serves as a 24/7 sales hub, automates customer bookings, and captures premium leads that would otherwise go to competitors.
- KEY PHRASE HIGHLIGHTS: "premium digital storefront", "custom homepage design", "mobile responsive", "automated booking system", "conversion rates".
"""
        else: # custom niche service
            persona_directive = f"Specialist, Local Consultant, and Solutions Expert in {service}"
            service_directives = f"""
- SERVICE TO PITCH: {service}.
- VALUE PROPOSITION: Focus on delivering top-tier value and growth for their business using {service}. Highlight how optimizing and deploying {service} solves their business growth, visibility, or operational needs. Connect the value proposition of {service} to bringing them more local client inquiries, conversions, and revenue.
- KEY PHRASE HIGHLIGHTS: "{service}", "growth consultant", "business optimization", "client conversion", "value proposition".
- SPECIAL DIRECTIVE: You must strictly combine this custom service description with any rules and details from the CUSTOM USER PROFILE & OUTREACH RULES (if provided below) to refine the pitch details and tone.
"""
        return persona_directive, service_directives
