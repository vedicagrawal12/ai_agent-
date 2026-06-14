import os
import requests
import json
import time
import yaml
import logging

class AIOutreachWriter:
    _prompts = None
    _prompts_mtime = 0  # Track file modification time for hot-reload

    @staticmethod
    def _load_prompts():
        """Load and cache prompt templates from outreach_pitches.yaml with hot-reload."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompts_path = os.path.join(base_dir, "prompts", "outreach_pitches.yaml")
        try:
            current_mtime = os.path.getmtime(prompts_path)
        except OSError:
            current_mtime = 0

        if AIOutreachWriter._prompts is None or current_mtime != AIOutreachWriter._prompts_mtime:
            try:
                with open(prompts_path, "r", encoding="utf-8") as f:
                    AIOutreachWriter._prompts = yaml.safe_load(f)
                AIOutreachWriter._prompts_mtime = current_mtime
                logging.debug(f"Prompts YAML loaded/reloaded (mtime={current_mtime})")
            except Exception as e:
                logging.error(f"Error loading prompts YAML from {prompts_path}: {e}")
                if AIOutreachWriter._prompts is None:
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
        language: str = "hinglish",
        audit_link: str = "",
        audit_data: dict = None
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

        if audit_data and audit_link:
            overall_score = audit_data.get("overall_score", 0)
            scores = audit_data.get("scores", {})
            recommendations = audit_data.get("recommendations", [])
            warnings_text = []
            for rec in recommendations:
                warnings_text.append(f"  - [{rec.get('category')}] {rec.get('title')}: {rec.get('description')}")
            warnings_str = "\n".join(warnings_text) if warnings_text else "  - None (website has a perfect score!)"
            
            audit_directive = f"""
- WEBSITE SEO & PERFORMANCE AUDIT RESULTS (CRITICAL: Mention these specific real-world data points and critical issues to show the prospect you did a real audit of their website):
  * Public Audit Report URL: {audit_link}
  * Overall Site Score: {overall_score}/100
  * Category Scores: Speed={scores.get('speed', 0)}/100, SEO={scores.get('seo', 0)}/100, Mobile Responsiveness={scores.get('mobile', 0)}/100, SSL Security={scores.get('ssl', 0)}/100, Image Alt Tags={scores.get('alt', 0)}/100
  * Key Identified Issues:
{warnings_str}
  * CRITICAL COPYWRITING DIRECTIVE: Mention specific low scores (e.g. speed, missing SSL, or missing viewport/mobile responsiveness) to create urgency, and invite them to view their complete public report card at {audit_link}.
"""
            custom_rules_directive += "\n" + audit_directive

        # Resolve persona and service directives based on target service
        persona_directive, service_directives = AIOutreachWriter._resolve_service_directives(service)

        # Resolve category-specific pain points and value propositions
        category_directives = AIOutreachWriter._resolve_category_directives(lead_data.get('category', ''))

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

            if website_url and is_broken:
                template = prompts.get("whatsapp_pitch_broken", "")
            elif website_url and not is_broken:
                template = prompts.get("whatsapp_pitch_working_website", "")
            else:
                template = prompts.get("whatsapp_pitch_no_website", "")

            if not template:
                template = prompts.get("whatsapp_pitch_no_website", "")

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
                language_directives=whatsapp_lang_dir,
                category_directives=category_directives
            )

        return AIOutreachWriter._call_gemini_api(prompt, api_key, tone=tone)

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
        language: str = "hinglish",
        audit_link: str = "",
        audit_data: dict = None
    ) -> str:
        """
        Generates a highly personalized, human-like sales cold email with a Subject Line and Body.
        """
        if not api_key:
            raise Exception("Gemini API key is required for AI generation.")

        custom_rules_directive = ""
        if custom_pitch_rules:
            custom_rules_directive = f"\n- CUSTOM USER PROFILE & OUTREACH RULES (CRITICAL: You must strictly incorporate these personalized preferences and details in your pitch writing):\n{custom_pitch_rules}\n"

        if audit_data and audit_link:
            overall_score = audit_data.get("overall_score", 0)
            scores = audit_data.get("scores", {})
            recommendations = audit_data.get("recommendations", [])
            warnings_text = []
            for rec in recommendations:
                warnings_text.append(f"  - [{rec.get('category')}] {rec.get('title')}: {rec.get('description')}")
            warnings_str = "\n".join(warnings_text) if warnings_text else "  - None (website has a perfect score!)"
            
            audit_directive = f"""
- WEBSITE SEO & PERFORMANCE AUDIT RESULTS (CRITICAL: Mention these specific real-world data points and critical issues to show the prospect you did a real audit of their website):
  * Public Audit Report URL: {audit_link}
  * Overall Site Score: {overall_score}/100
  * Category Scores: Speed={scores.get('speed', 0)}/100, SEO={scores.get('seo', 0)}/100, Mobile Responsiveness={scores.get('mobile', 0)}/100, SSL Security={scores.get('ssl', 0)}/100, Image Alt Tags={scores.get('alt', 0)}/100
  * Key Identified Issues:
{warnings_str}
  * CRITICAL COPYWRITING DIRECTIVE: Mention specific low scores (e.g. speed, missing SSL, or missing viewport/mobile responsiveness) to create urgency, and invite them to view their complete public report card at {audit_link}.
"""
            custom_rules_directive += "\n" + audit_directive

        # Resolve persona and service directives based on target service
        persona_directive, service_directives = AIOutreachWriter._resolve_service_directives(service)

        # Resolve category-specific pain points and value propositions
        category_directives = AIOutreachWriter._resolve_category_directives(lead_data.get('category', ''))

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
            language_directives=email_lang_dir,
            category_directives=category_directives
        )


        return AIOutreachWriter._call_gemini_api(prompt, api_key, tone=tone)

    @staticmethod
    def _call_gemini_api(prompt: str, api_key: str, tone: str = "elite") -> str:
        """Helper method to handle the stateless requests to the Google Gemini API."""
        if not api_key.startswith("AIza") and not api_key.startswith("AQ."):
            logging.warning("WARNING: Gemini API Key does not start with standard 'AIza' or 'AQ.' prefix. Proceeding anyway.")

        # Fixed optimal settings — temperature varies by tone, not prompt length
        max_output_tokens = 4096
        request_timeout = 50
        if tone == "friendly":
            temperature = 0.88
        elif tone == "direct":
            temperature = 0.72
        else:  # elite
            temperature = 0.82

        # Smart static model list — no fragile discovery API call
        final_models = [
            ("v1beta", "gemini-2.5-flash"),
            ("v1beta", "gemini-2.5-pro"),
            ("v1beta", "gemini-2.0-flash"),
            ("v1beta", "gemini-2.0-flash-lite"),
            ("v1beta", "gemini-3.5-flash"),
            ("v1", "gemini-1.5-flash"),
            ("v1", "gemini-1.5-pro"),
            ("v1beta", "gemini-pro")
        ]

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

    @staticmethod
    def _resolve_category_directives(category: str) -> str:
        """Map business category to industry-specific pain points, urgency hooks, and CTA alignment."""
        cat = (category or "").lower().strip()

        # ── Health & Fitness ──
        if any(k in cat for k in ['gym', 'fitness', 'yoga', 'crossfit', 'workout', 'pilates', 'martial art', 'boxing', 'zumba']):
            return """
- CATEGORY INTELLIGENCE (Health & Fitness):
  * PAIN POINTS: Membership churn is #1 killer — members sign up via Google but leave if online booking, class schedules, and trainer profiles aren't frictionless. Competitors with slick apps steal walk-in traffic.
  * URGENCY: Peak season (New Year, summer body) drives 60% of annual sign-ups. If their digital funnel isn't ready, they lose to the gym down the street that has online trials.
  * CTA ALIGNMENT: Offer a live mockup showing class schedule integration, trainer profiles grid, and online trial-booking flow.
"""
        # ── Medical & Healthcare ──
        if any(k in cat for k in ['dentist', 'dental', 'clinic', 'doctor', 'hospital', 'dermatolog', 'physician', 'ortho', 'eye', 'optic', 'physio', 'chiro', 'ayurved', 'homeopath', 'pharma', 'patholog', 'diagnostic']):
            return """
- CATEGORY INTELLIGENCE (Medical & Healthcare):
  * PAIN POINTS: Patients research heavily before choosing a doctor — 77% check online reviews and website credibility. A missing or outdated website destroys trust instantly. Appointment no-shows spike when there's no online booking.
  * URGENCY: Local competitors with clean, trustworthy websites and Google My Business profiles are capturing patients who would otherwise walk into their clinic.
  * CTA ALIGNMENT: Offer a mockup showing doctor profiles, specialization pages, patient testimonials, and an integrated appointment booking system.
"""
        # ── Beauty & Wellness ──
        if any(k in cat for k in ['salon', 'spa', 'parlour', 'parlor', 'barber', 'beauty', 'nail', 'hair', 'makeup', 'grooming', 'skin care', 'skincare', 'tattoo', 'mehndi', 'bridal']):
            return """
- CATEGORY INTELLIGENCE (Beauty & Wellness):
  * PAIN POINTS: Beauty clients are hyper-visual — they choose salons based on Instagram aesthetic and website portfolio. 85% of premium clients book online, not by walk-in. No digital presence = invisible to the most profitable customer segment.
  * URGENCY: Wedding/festive seasons drive 3x booking volume. Competitors with Instagram feeds and online slot booking are stealing their premium bridal/party clients.
  * CTA ALIGNMENT: Offer a mockup showcasing a visual service menu, before/after gallery, stylist profiles, and online slot booking with WhatsApp confirmation.
"""
        # ── Food & Hospitality ──
        if any(k in cat for k in ['restaurant', 'cafe', 'hotel', 'bakery', 'bar', 'dhaba', 'food', 'dine', 'dining', 'catering', 'sweet', 'pizza', 'biryani', 'juice', 'tea', 'coffee', 'lounge', 'pub', 'banquet', 'resort']):
            return """
- CATEGORY INTELLIGENCE (Food & Hospitality):
  * PAIN POINTS: 90% of diners check Google reviews and menus online before visiting. No website = they rely entirely on Zomato/Swiggy, paying 25-30% commission on every order. A direct website with online ordering captures these margins.
  * URGENCY: Weekend/festival rushes and delivery demand spikes mean lost revenue if there's no direct booking/ordering channel. Competitors with branded websites and Google ordering links are stealing margin-rich direct orders.
  * CTA ALIGNMENT: Offer a mockup showing a visual menu with photos, table reservation system, direct ordering page, and Google Maps integration.
"""
        # ── Education & Coaching ──
        if any(k in cat for k in ['school', 'coaching', 'tutor', 'academy', 'institute', 'training', 'education', 'college', 'university', 'preschool', 'playschool', 'nursery', 'classes', 'learning']):
            return """
- CATEGORY INTELLIGENCE (Education & Coaching):
  * PAIN POINTS: Parents research extensively — a professional website with course details, faculty profiles, and results/testimonials is the #1 trust factor. Coaching centers without digital presence lose to competitors who showcase toppers and success stories online.
  * URGENCY: Admission season is time-bound. Parents comparing options will skip any institute that looks unprofessional or has no online presence.
  * CTA ALIGNMENT: Offer a mockup showing course catalog, batch schedules, faculty profiles, results showcase, and online admission inquiry/registration form.
"""
        # ── Automotive ──
        if any(k in cat for k in ['garage', 'car wash', 'mechanic', 'automobile', 'auto', 'bike', 'vehicle', 'tyre', 'tire', 'car dealer', 'showroom', 'service center', 'service centre']):
            return """
- CATEGORY INTELLIGENCE (Automotive):
  * PAIN POINTS: Vehicle owners search "near me" during emergencies (breakdown, flat tire). If the business doesn't appear on Google with clear services, pricing, and click-to-call, they lose to the first competitor who does.
  * URGENCY: Every day without proper Google visibility = lost emergency and routine service customers going to competitors.
  * CTA ALIGNMENT: Offer a mockup showing service catalog with transparent pricing, online service booking, emergency contact CTA, and customer reviews showcase.
"""
        # ── Real Estate & Construction ──
        if any(k in cat for k in ['builder', 'property', 'real estate', 'architect', 'interior', 'construction', 'contractor', 'developer', 'flat', 'apartment', 'villa', 'plot']):
            return """
- CATEGORY INTELLIGENCE (Real Estate & Construction):
  * PAIN POINTS: Property buyers expect virtual tours, floor plans, and project galleries. A missing or basic website kills credibility for high-ticket transactions. 70% of property research starts online.
  * URGENCY: New project launches need immediate digital presence to capture early buyer interest. Competitors with polished project microsites are winning premium leads.
  * CTA ALIGNMENT: Offer a mockup showing project gallery with floor plans, virtual tour integration, EMI calculator, and lead capture form with callback scheduling.
"""
        # ── Legal & Finance ──
        if any(k in cat for k in ['lawyer', 'advocate', 'legal', 'ca ', 'chartered', 'accountant', 'tax', 'consultant', 'financial', 'insurance', 'loan', 'investment']):
            return """
- CATEGORY INTELLIGENCE (Legal & Finance):
  * PAIN POINTS: Clients seeking legal/financial services prioritize credibility and expertise. A professional website with case studies, practice areas, and client testimonials builds trust that word-of-mouth alone cannot scale.
  * URGENCY: Competitor firms with polished digital presence are capturing high-value clients who search online for specialized legal/financial services.
  * CTA ALIGNMENT: Offer a mockup showing practice areas, attorney/CA profiles, client testimonials, and a confidential consultation booking form.
"""
        # ── Pet Services ── (must be checked BEFORE Retail since 'pet shop' contains 'shop')
        if any(k in cat for k in ['pet ', 'pets', 'veterinary', 'vet ', 'animal', 'dog ', 'dogs', 'puppy', 'kitten', 'grooming', 'kennel', 'aquarium']):
            return """
- CATEGORY INTELLIGENCE (Pet Services):
  * PAIN POINTS: Pet parents are emotionally invested and research extensively. They want to see facility photos, vet qualifications, and read reviews before trusting someone with their pet. No online presence = no trust.
  * URGENCY: Seasonal demand spikes (vacation boarding, monsoon health issues) drive urgent searches. Being invisible online means losing to the vet/groomer who shows up first on Google.
  * CTA ALIGNMENT: Offer a mockup showing services menu, facility gallery, vet profiles, pet health tips blog, and online appointment booking.
"""
        # ── Retail & E-commerce ──
        if any(k in cat for k in ['shop', 'store', 'boutique', 'showroom', 'electronics', 'furniture', 'jewel', 'clothing', 'garment', 'fashion', 'textile', 'gift', 'handicraft', 'grocery', 'supermarket', 'kirana', 'medical store']):
            return """
- CATEGORY INTELLIGENCE (Retail & E-commerce):
  * PAIN POINTS: Local shops compete with Amazon/Flipkart. Without a digital catalog and WhatsApp ordering, they lose customers who want to browse and buy conveniently. 65% of local shoppers check product availability online before visiting.
  * URGENCY: Festival/sale seasons drive massive purchase intent. Shops without product catalogs and offers pages online miss the wave entirely.
  * CTA ALIGNMENT: Offer a mockup showing visual product catalog with categories, WhatsApp order button, store location with directions, and seasonal offers banner.
"""
        # ── Events & Creative ──
        if any(k in cat for k in ['photographer', 'photography', 'wedding', 'event', 'planner', 'dj', 'decoration', 'florist', 'caterer', 'videograph', 'studio', 'music', 'band', 'anchor']):
            return """
- CATEGORY INTELLIGENCE (Events & Creative):
  * PAIN POINTS: Clients hire based on portfolio quality. Without a stunning visual portfolio website, they can only showcase work on Instagram which limits SEO discoverability. Competitors with dedicated portfolio sites rank higher and close more bookings.
  * URGENCY: Wedding/event seasons are short and intense. Couples research 3-6 months in advance. If the portfolio isn't discoverable online during research phase, the booking window closes.
  * CTA ALIGNMENT: Offer a mockup showing a cinematic portfolio gallery, service packages with pricing, client testimonials, and an availability/booking inquiry form.
"""
        # ── Home Services ──
        if any(k in cat for k in ['plumber', 'electrician', 'painter', 'pest control', 'ac repair', 'cleaning', 'laundry', 'packers', 'movers', 'carpenter', 'locksmith', 'water purifier', 'solar', 'cctv', 'security']):
            return """
- CATEGORY INTELLIGENCE (Home Services):
  * PAIN POINTS: Home service searches are 90% "near me" and emergency-driven. If the business doesn't show up on Google Maps with clear services, pricing, and one-tap calling, they lose the job to the competitor who does.
  * URGENCY: Every missed "near me" search is a lost customer going to Urban Company or the first Google result. Speed of response = speed of revenue.
  * CTA ALIGNMENT: Offer a mockup showing service area coverage map, transparent pricing table, one-tap call/WhatsApp CTA, and customer review showcase.
"""
        # ── Travel & Transport ──
        if any(k in cat for k in ['travel', 'tour', 'taxi', 'cab', 'courier', 'logistics', 'transport', 'bus', 'flight', 'visa', 'passport', 'rental', 'car rental']):
            return """
- CATEGORY INTELLIGENCE (Travel & Transport):
  * PAIN POINTS: Travelers compare packages and prices online. Without a website showing itineraries, pricing, and booking options, they lose to MakeMyTrip/Goibibo and competitors with online presence.
  * URGENCY: Travel is seasonal and intent-driven. Customers searching during peak seasons book from whoever has the most professional and trustworthy online setup.
  * CTA ALIGNMENT: Offer a mockup showing travel packages with photos, itinerary builder, instant quote request, and WhatsApp booking integration.
"""
        # ── Hostel & Accommodation ──
        if any(k in cat for k in ['hostel', 'pg', 'paying guest', 'stay', 'accommodation', 'lodge', 'guest house', 'homestay', 'dormitory']):
            return """
- CATEGORY INTELLIGENCE (Hostel & Accommodation):
  * PAIN POINTS: Students and travelers compare hostels online — photos, amenities, pricing, and reviews drive decisions. Without a website, they rely entirely on OYO/Hostelworld commissions (15-25%).
  * URGENCY: Admission season and tourist seasons drive massive demand. Direct bookings via their own website save commission and build a customer database.
  * CTA ALIGNMENT: Offer a mockup showing room gallery, amenity highlights, transparent pricing, location map, and direct booking form with WhatsApp confirmation.
"""
        # ── General / Unknown Category (Fallback) ──
        return """
- CATEGORY INTELLIGENCE (Local Business - General):
  * PAIN POINTS: Modern customers expect every business to have a professional digital presence. 88% of consumers research online before visiting a local business. No website or poor online visibility = lost trust and lost customers.
  * URGENCY: Every day without a strong digital presence, potential customers are choosing competitors who appear more professional and accessible online.
  * CTA ALIGNMENT: Offer a custom mockup/draft tailored to their specific business type showing professional branding, service showcase, and customer inquiry/booking capability.
"""
