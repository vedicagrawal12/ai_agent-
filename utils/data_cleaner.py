"""
Data Cleaner — Deduplication, phone standardization, and data normalization.

Ensures all collected lead data is clean, consistent, and ready for outreach.
"""

import re
import concurrent.futures
from typing import List
from constants import WEBSITE_CHECK_MAX_WORKERS, WEBSITE_CHECK_TIMEOUT, WEBSITE_CHECK_MAX_SITES
import phonenumbers
from phonenumbers import PhoneNumberType
from collectors.base_collector import Lead
import logging
import requests


class DataCleaner:
    """Cleans and normalizes lead data."""

    @staticmethod
    def standardize_phone(phone: str) -> str:
        """
        Standardize phone number to a consistent format.
        
        Converts various formats:
        - "09876543210" → "+91 98765 43210"
        - "9876543210" → "+91 98765 43210"
        - "+919876543210" → "+91 98765 43210"
        """
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        digits = re.sub(r'[^\d]', '', phone)
        
        # Handle Indian numbers
        if digits.startswith('91') and len(digits) == 12:
            # Already has country code
            return f"+91 {digits[2:7]} {digits[7:]}"
        elif digits.startswith('0') and len(digits) == 11:
            # Has leading 0
            digits = digits[1:]
            return f"+91 {digits[:5]} {digits[5:]}"
        elif len(digits) == 10:
            # Local number without country code
            return f"+91 {digits[:5]} {digits[5:]}"
        else:
            # Return as-is if format is unrecognized, but add + prefix
            if phone.startswith('+'):
                return phone
            return f"+{digits}" if digits else ""

    @staticmethod
    def extract_whatsapp_number(phone: str) -> str:
        """
        Extract digits-only WhatsApp number from a formatted phone.
        WhatsApp needs: country code + number, no spaces/symbols.
        e.g. "+91 98765 43210" → "919876543210"
        """
        if not phone:
            return ""
        digits = re.sub(r'[^\d]', '', phone)
        # Indian numbers need 91 prefix
        if len(digits) == 10:
            return f"91{digits}"
        elif len(digits) == 12 and digits.startswith('91'):
            return digits
        elif len(digits) == 11 and digits.startswith('0'):
            return f"91{digits[1:]}"
        return digits if len(digits) >= 10 else ""

    @staticmethod
    def assign_priority(lead: Lead) -> str:
        """
        Assign priority based on website presence and review count.
        
        Priority logic:
        - IGNORE: Has a working website (not our target audience)
        - HIGH:   No website (or broken website!), has phone, < 50 reviews (needs help the most)
        - MEDIUM: No website (or broken website!), has phone, 50–200 reviews
        - LOW:    No website, no phone OR > 200 reviews
        """
        # If they have a website but it is NOT broken, we ignore them (not our audience)
        if lead.website and not lead.is_broken_website:
            return "IGNORE"
        
        has_phone = bool(lead.phone)
        reviews = lead.reviews or 0
        
        # If they have a broken website, they are premium targets! Bump them to HIGH/MEDIUM
        if lead.is_broken_website:
            if has_phone and reviews < 50:
                return "HIGH"
            elif has_phone and reviews <= 200:
                return "MEDIUM"
            else:
                return "HIGH" # Broken websites are goldmines, keep them high priority!
        
        if has_phone and reviews < 50:
            return "HIGH"
        elif has_phone and reviews <= 200:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def validate_and_classify_phone(phone: str, default_region: str = "IN") -> dict:
        """
        Validate and classify a phone number using phonenumbers library.
        Args:
            phone: Raw phone string
            default_region: ISO country code for parsing ambiguous numbers (default: 'IN' for India)
        Returns:
            {"is_valid": bool, "whatsapp_number": str, "line_type": str}
        """
        if not phone:
            return {"is_valid": False, "whatsapp_number": "", "line_type": "UNKNOWN"}
            
        try:
            # BUG-L2 fix: Use configurable region instead of hardcoded "IN"
            parsed = phonenumbers.parse(phone, default_region)
            is_valid = phonenumbers.is_valid_number(parsed)
            
            if not is_valid:
                return {"is_valid": False, "whatsapp_number": "", "line_type": "UNKNOWN"}
                
            # Convert to international format without plus or symbols for WhatsApp (e.g. 919876543210)
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            whatsapp_number = formatted.replace("+", "")
            
            # Determine line type
            num_type = phonenumbers.number_type(parsed)
            line_type = "UNKNOWN"
            if num_type == PhoneNumberType.MOBILE:
                line_type = "MOBILE"
            elif num_type in [PhoneNumberType.FIXED_LINE, PhoneNumberType.FIXED_LINE_OR_MOBILE]:
                line_type = "LANDLINE"
                if num_type == PhoneNumberType.FIXED_LINE_OR_MOBILE:
                    line_type = "MOBILE" # Default to mobile if ambiguous
            elif num_type == PhoneNumberType.VOIP:
                line_type = "VOIP"
                
            return {
                "is_valid": True,
                "whatsapp_number": whatsapp_number,
                "line_type": line_type
            }
        except Exception as e:
            logging.error(f"Error parsing phone {phone}: {e}")
            return {"is_valid": False, "whatsapp_number": "", "line_type": "UNKNOWN"}

    # Blocked internal/private hostnames and IP ranges (SSRF protection)
    BLOCKED_HOSTNAMES = {'localhost', '127.0.0.1', '0.0.0.0', '::1', 'metadata.google.internal'}

    @classmethod
    def _is_safe_url(cls, url: str) -> bool:
        """
        SSRF protection — block requests to internal/private IPs.
        Returns True if URL is safe to fetch, False if it targets an internal resource.
        """
        try:
            from urllib.parse import urlparse
            import socket
            import ipaddress
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
            
            # Block known dangerous hostnames
            if hostname in cls.BLOCKED_HOSTNAMES:
                return False
            
            # Resolve hostname to IP and check if it's private
            try:
                resolved_ip = socket.gethostbyname(hostname)
                ip_obj = ipaddress.ip_address(resolved_ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                    return False
            except socket.gaierror:
                pass
            
            return True
        except Exception:
            return False

    @classmethod
    def _safe_request(cls, url: str, method: str, headers: dict, timeout: float = 2.0, max_redirects: int = 5) -> requests.Response:
        from urllib.parse import urljoin
        current_url = url
        for _ in range(max_redirects):
            if not cls._is_safe_url(current_url):
                raise Exception(f"Blocked request to unsafe URL: {current_url}")
                
            if method.upper() == "HEAD":
                response = requests.head(current_url, headers=headers, timeout=timeout, allow_redirects=False)
            else:
                response = requests.get(current_url, headers=headers, timeout=timeout, allow_redirects=False, stream=True)
                
            if response.is_redirect or (300 <= response.status_code < 400):
                next_url = response.headers.get('Location')
                if not next_url:
                    break
                current_url = urljoin(current_url, next_url)
            else:
                return response
        raise Exception("Too many redirects or redirection loops detected.")

    @staticmethod
    def check_website_health(url: str) -> bool:
        """
        Perform a lightweight HTTP HEAD/GET request to test if a website is online/active.
        Returns True if working (any server response), False if broken (network exception/DNS failure).
        Optimized: reduced timeouts, HEAD 405/501 treated as alive (BUG #13/#14 fix).
        """
        if not url:
            return False
            
        # Clean URL
        target_url = url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = "https://" + target_url
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            # 1. Try fast HEAD request first (2s timeout instead of 3s)
            response = DataCleaner._safe_request(target_url, "HEAD", headers=headers, timeout=2.0)
            # Any response under 500 means server is alive (405 = HEAD not supported, still alive!)
            if response.status_code < 500:
                return True
            # 5xx means server error — try GET to confirm
        except requests.exceptions.SSLError:
            # BUG-H6 fix: SSL cert issues mean server IS alive, just misconfigured cert
            return True
        except requests.exceptions.ConnectionError:
            return False  # DNS/network failure = broken
        except requests.exceptions.Timeout:
            pass  # Timeout on HEAD — fall through to GET
        except Exception:
            pass
            
        try:
            # 2. Fallback GET only if HEAD timed out or returned 5xx
            response = DataCleaner._safe_request(target_url, "GET", headers=headers, timeout=2.0)
            response.close()  # Close immediately — we only need the status code
            if response.status_code < 500:
                return True
        except requests.exceptions.SSLError:
            # BUG-H6 fix: Same as above — server is alive
            return True
        except Exception:
            pass
            
        return False

    @staticmethod
    def remove_duplicates(leads: List[Lead]) -> List[Lead]:
        """
        Remove duplicate leads based on place_id, phone number, and name similarity.
        
        Deduplication strategy:
        1. First pass: exact place_id match
        2. Second pass: same phone number
        3. Third pass: very similar names at same address
        """
        seen_ids = set()
        seen_phones = set()
        seen_names = set()
        unique_leads = []

        for lead in leads:
            # Skip if we've seen this place_id
            if lead.place_id and lead.place_id in seen_ids:
                continue

            # Standardize phone digits for duplicate check
            phone_digits = re.sub(r'\D', '', lead.phone) if lead.phone else ""
            if phone_digits and phone_digits in seen_phones:
                continue

            # Match by normalized name + city
            name_key = f"{lead.name.lower().strip()}_{lead.city.lower().strip()}"
            if name_key in seen_names:
                continue

            # Mark as seen
            if lead.place_id:
                seen_ids.add(lead.place_id)
            if phone_digits:
                seen_phones.add(phone_digits)
            seen_names.add(name_key)
            unique_leads.append(lead)

        return unique_leads

    @staticmethod
    def clean_leads(leads: List[Lead]) -> List[Lead]:
        """
        Clean and normalize a list of leads:
        1. Standardize phone numbers and classify line types (Mobile vs Landline)
        2. Perform parallel website status checks to identify broken websites
        3. Clean names, addresses, cities, and categories
        4. Assign priority scores based on website health & review volumes
        """
        # 1. Parse and standardize phone numbers using phonenumbers
        for lead in leads:
            # Clean name, address, city, category
            lead.name = lead.name.strip()
            lead.address = lead.address.strip()
            lead.city = lead.city.strip().title()
            lead.category = lead.category.strip().title() if lead.category else "Other"
            
            # Check phone validity and line type
            phone_data = DataCleaner.validate_and_classify_phone(lead.phone)
            if phone_data["is_valid"]:
                lead.whatsapp_number = phone_data["whatsapp_number"]
                lead.line_type = phone_data["line_type"]
                # Format phone visually
                lead.phone = DataCleaner.standardize_phone(lead.phone)
            else:
                # Fallback to legacy regex cleaning
                lead.whatsapp_number = DataCleaner.extract_whatsapp_number(lead.phone)
                lead.phone = DataCleaner.standardize_phone(lead.phone)
                lead.line_type = "MOBILE" if lead.whatsapp_number else "UNKNOWN"

        # 2. Parallel Website status check (Only test leads that HAVE a website listed)
        leads_with_websites = [l for l in leads if l.website]
        if leads_with_websites:
            # BUG-M5 fix: Cap at max websites to check — beyond that, skip (not worth the delay)
            if len(leads_with_websites) > WEBSITE_CHECK_MAX_SITES:
                logging.info(f"Limiting website health checks to {WEBSITE_CHECK_MAX_SITES} of {len(leads_with_websites)} leads")
                leads_with_websites = leads_with_websites[:WEBSITE_CHECK_MAX_SITES]
            logging.info(f"Checking health of {len(leads_with_websites)} websites in parallel...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=WEBSITE_CHECK_MAX_WORKERS) as executor:
                # Map futures
                future_to_lead = {
                    executor.submit(DataCleaner.check_website_health, l.website): l 
                    for l in leads_with_websites
                }
                try:
                    # BUG-M5 fix: Reduced global timeout from 30s to WEBSITE_CHECK_TIMEOUT for faster search responses
                    for future in concurrent.futures.as_completed(future_to_lead, timeout=WEBSITE_CHECK_TIMEOUT):
                        lead = future_to_lead[future]
                        try:
                            is_online = future.result()
                            # If NOT online, mark as broken website!
                            lead.is_broken_website = False if is_online else True
                        except Exception as e:
                            logging.error(f"Error checking website for {lead.name}: {e}")
                            lead.is_broken_website = True # Treat failures as broken
                except concurrent.futures.TimeoutError:
                    logging.warning(f"Warning: Website health check timed out after {WEBSITE_CHECK_TIMEOUT}s. Marking remaining as broken.")
                    for future, lead in future_to_lead.items():
                        if not future.done():
                            lead.is_broken_website = True
                            future.cancel()
                except Exception as loop_err:
                    logging.error(f"Error during parallel website checks: {loop_err}")

        # 3. Assign priority based on website status & reviews
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "IGNORE": 3}
        for lead in leads:
            lead.priority = DataCleaner.assign_priority(lead)

        # 4. Remove duplicates
        leads = DataCleaner.remove_duplicates(leads)

        # 5. Sort by priority
        leads.sort(key=lambda l: priority_order.get(l.priority, 3))

        return leads

    @staticmethod
    def filter_leads(leads: List[Lead], include_with_website: bool = False) -> List[Lead]:
        """
        Filter leads based on criteria.
        
        Args:
            leads: List of leads to filter
            include_with_website: If False, removes businesses with working websites (IGNORE priority)
            
        Returns:
            Filtered list of leads
        """
        if include_with_website:
            return leads
        
        # Keep all leads that are NOT in IGNORE priority
        # (Broken website leads are never IGNORE since assign_priority gives them HIGH/MEDIUM)
        return [lead for lead in leads if lead.priority != "IGNORE"]
