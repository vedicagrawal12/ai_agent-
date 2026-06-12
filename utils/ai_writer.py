import os
import requests
import json
import time
import yaml
import logging

class AIOutreachWriter:
    _prompts = None

    @staticmethod
    def _load_prompts():
        """Load and cache prompt templates from outreach_pitches.yaml."""
        if AIOutreachWriter._prompts is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompts_path = os.path.join(base_dir, "prompts", "outreach_pitches.yaml")
            try:
                with open(prompts_path, "r", encoding="utf-8") as f:
                    AIOutreachWriter._prompts = yaml.safe_load(f)
            except Exception as e:
                logging.error(f"Error loading prompts YAML from {prompts_path}: {e}")
                AIOutreachWriter._prompts = {}
        return AIOutreachWriter._prompts

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
        min_words: int = 150,
        language: str = "hinglish"
    ) -> str:
        """
        Generates a highly personalized, human-like sales pitch using the Gemini API.
        Templates are loaded dynamically from yaml.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        custom_rules_directive = ""
        if custom_pitch_rules:
            custom_rules_directive = f"\n- CUSTOM USER PROFILE & OUTREACH RULES (CRITICAL: You must strictly incorporate these personalized preferences and details in your pitch writing):\n{custom_pitch_rules}\n"

        # Resolve persona and service directives based on target service
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
- SMART HOOK (ESTABLISHED AUTHORITY): This local business has a massive review count ({reviews_count} reviews) and is clearly an established local favorite. Frame the pitch around scaling, keeping up with demand, and retaining premium customers who prefer quick booking interfaces.
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

        # Resolve language directives for WhatsApp
        lang_lower = (language or "hinglish").lower().strip()
        if lang_lower == "english":
            whatsapp_lang_dir = "- LANGUAGE: Must be written in pure, grammatically correct, professional and natural English. Do NOT use Hinglish or Hindi words."
            refine_lang_dir = "Keep the natural, conversational, polite English tone. Do NOT use Hinglish or Hindi words."
        elif lang_lower == "hindi":
            whatsapp_lang_dir = "- LANGUAGE: Must be written in pure, grammatically correct and natural Hindi written in Devanagari script. Do NOT use English script, but you may use technical terms transliterated or written in Devanagari (e.g. सेटअप, वेबसाइट, Leads, etc.)."
            refine_lang_dir = "Keep the natural, conversational, polite Hindi tone written in Devanagari script. Do NOT use English script."
        else: # hinglish
            whatsapp_lang_dir = "- LANGUAGE: Must be highly natural, conversational Hinglish (using Latin/English script) as spoken in India. Mix Hindi and English words naturally. Use words like: *setup*, *vibe*, *fuss*, *traffic*, *leads*, *look*, *draft*, *leakage*, *switch*."
            refine_lang_dir = "Keep the natural, conversational, polite Hinglish tone, mixing Hindi and English words naturally."

        prompts = AIOutreachWriter._load_prompts()

        # Build the prompt with dynamic context
        if refine_feedback and previous_pitch:
            template = prompts.get("whatsapp_pitch_refine", "")
            prompt = template.format(
                custom_rules_directive=custom_rules_directive,
                business_name=lead_data.get('name', 'Business'),
                city=lead_data.get('city', 'your city'),
                category=lead_data.get('category', 'Business'),
                previous_pitch=previous_pitch,
                refine_feedback=refine_feedback,
                language_directives=refine_lang_dir
            )
        else:
            is_broken = bool(lead_data.get('is_broken_website'))
            website_url = lead_data.get('website', '')

            if is_broken:
                template = prompts.get("whatsapp_pitch_broken", "")
                prompt = template.format(
                    persona_directive=persona_directive,
                    business_name=lead_data.get('name', 'Business'),
                    category=lead_data.get('category', 'Business'),
                    city=lead_data.get('city', 'your city'),
                    rating=lead_data.get('rating', '0'),
                    reviews=lead_data.get('reviews', '0'),
                    website_url=website_url,
                    custom_rules_directive=custom_rules_directive,
                    mockup_link=mockup_link,
                    project_sample=project_sample,
                    service_directives=service_directives,
                    tone_directives=tone_directives,
                    length_directives=length_directives,
                    hook_type_directive=hook_type_directive,
                    signoff_directive=signoff_directive,
                    language_directives=whatsapp_lang_dir
                )
            else:
                template = prompts.get("whatsapp_pitch_no_website", "")
                prompt = template.format(
                    persona_directive=persona_directive,
                    business_name=lead_data.get('name', 'Business'),
                    category=lead_data.get('category', 'Business'),
                    city=lead_data.get('city', 'your city'),
                    rating=lead_data.get('rating', '0'),
                    reviews=lead_data.get('reviews', '0'),
                    custom_rules_directive=custom_rules_directive,
                    mockup_link=mockup_link,
                    project_sample=project_sample,
                    service_directives=service_directives,
                    tone_directives=tone_directives,
                    length_directives=length_directives,
                    hook_type_directive=hook_type_directive,
                    signoff_directive=signoff_directive,
                    language_directives=whatsapp_lang_dir
                )

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
        min_words: int = 150,
        language: str = "hinglish"
    ) -> str:
        """
        Generates a highly personalized, human-like sales cold email with a Subject Line and Body.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        custom_rules_directive = ""
        if custom_pitch_rules:
            custom_rules_directive = f"\n- CUSTOM USER PROFILE & OUTREACH RULES (CRITICAL: You must strictly incorporate these personalized preferences and details in your pitch writing):\n{custom_pitch_rules}\n"

        # Resolve persona and service directives based on target service
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
            
        is_broken = bool(lead_data.get('is_broken_website'))
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

        # Resolve language directives for Email
        lang_lower = (language or "hinglish").lower().strip()
        if lang_lower == "english":
            email_lang_dir = "LANGUAGE: Pure, grammatically correct, professional and natural English. Do NOT use Hinglish or Hindi words. Follow English syntax and grammar strictly."
        elif lang_lower == "hindi":
            email_lang_dir = "LANGUAGE: Pure, grammatically correct and natural Hindi written in Devanagari script. Do NOT use English script, but you may use technical terms transliterated or written in Devanagari (e.g. सेटअप, वेबसाइट, Leads, etc.)."
        else: # hinglish
            email_lang_dir = "LANGUAGE: Natural conversational Hinglish (using Latin/English script) as spoken in casual business conversations in India. Mix Hindi and English words naturally. Use words like: *setup*, *vibe*, *fuss*, *traffic*, *leads*, *look*, *draft*, *leakage*, *switch*."

        prompts = AIOutreachWriter._load_prompts()
        template = prompts.get("email_pitch", "")
        
        if website_url:
            website_state = f"Has a working website listed: {website_url}" if not is_broken else f"Broken/Down listed URL: {website_url}"
        else:
            website_state = "DOES NOT HAVE A WEBSITE YET"
            
        prompt = template.format(
            business_name=lead_data.get('name', 'Business'),
            category=lead_data.get('category', 'Business'),
            city=lead_data.get('city', 'your city'),
            rating=lead_data.get('rating', '0'),
            reviews=lead_data.get('reviews', '0'),
            website_state=website_state,
            custom_rules_directive=custom_rules_directive,
            project_sample=project_sample,
            mockup_link=mockup_link,
            service_directives=service_directives,
            tone_directives=tone_directives,
            email_length_directives=email_length_directives,
            min_words=min_words,
            signoff_str=signoff_str,
            language_directives=email_lang_dir
        )


        return AIOutreachWriter._call_gemini_api(prompt, api_key)

    @staticmethod
    def _call_gemini_api(prompt: str, api_key: str) -> str:
        """Helper method to handle the stateless requests to the Google Gemini API."""
        if not api_key.startswith("AIza") and not api_key.startswith("AQ."):
            logging.warning("WARNING: Gemini API Key does not start with standard 'AIza' or 'AQ.' prefix. Proceeding anyway.")

        prompt_len = len(prompt)
        if prompt_len > 4000:
            max_output_tokens = 2048
            temperature = 0.85
            request_timeout = 45
        elif prompt_len > 2500:
            max_output_tokens = 1500
            temperature = 0.8
            request_timeout = 35
        else:
            max_output_tokens = 1024
            temperature = 0.75
            request_timeout = 25

        discovered_models = []
        try:
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
        except Exception:
            pass

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
                    response = requests.post(url, headers=headers, json=payload, timeout=request_timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            finish_reason = candidates[0].get("finishReason", "")
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                word_count = len(text.split())
                                if finish_reason == "MAX_TOKENS" and word_count < 100:
                                    last_error = "Output truncated (MAX_TOKENS)"
                                    break
                                return text.strip()
                    
                    try:
                        error_data = response.json()
                        last_error = error_data.get("error", {}).get("message", f"Status {response.status_code}")
                    except Exception:
                        last_error = f"Status {response.status_code}"
                    
                    if "key not valid" in last_error.lower() or "api key not valid" in last_error.lower() or "invalid api key" in last_error.lower():
                        raise Exception("Invalid Gemini API Key. Google API keys must start with 'AIza' or 'AQ.'. Please check your key in Settings.")
                    
                    if not primary_error:
                        primary_error = last_error
                    
                    is_retryable = (
                        response.status_code in [429, 500, 503] or
                        any(keyword in last_error.lower() for keyword in ["demand", "rate limit", "quota", "overloaded", "resource exhausted", "limit exceeded", "temp", "busy"])
                    )
                    
                    if is_retryable and attempt < max_retries:
                        sleep_time = 2.0 * (attempt + 1)
                        time.sleep(sleep_time)
                        continue
                    break
                    
                except requests.exceptions.Timeout:
                    last_error = "Request timed out."
                    if not primary_error:
                        primary_error = last_error
                    if attempt < max_retries:
                        sleep_time = 2.0 * (attempt + 1)
                        time.sleep(sleep_time)
                        continue
                    break
                except Exception as e:
                    if "Invalid Gemini API Key" in str(e):
                        raise e
                    last_error = str(e)
                    if not primary_error:
                        primary_error = last_error
                    if attempt < max_retries:
                        sleep_time = 2.0 * (attempt + 1)
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
