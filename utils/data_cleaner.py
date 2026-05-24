"""
Data Cleaner — Deduplication, phone standardization, and data normalization.

Ensures all collected lead data is clean, consistent, and ready for outreach.
"""

import re
from typing import List
from collectors.base_collector import Lead


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
        - IGNORE: Has a website (not our target audience)
        - HIGH:   No website, has phone, < 50 reviews (needs help the most)
        - MEDIUM: No website, has phone, 50–200 reviews
        - LOW:    No website, no phone OR > 200 reviews
        """
        if lead.website:
            return "IGNORE"
        
        has_phone = bool(lead.phone)
        reviews = lead.reviews or 0
        
        if has_phone and reviews < 50:
            return "HIGH"
        elif has_phone and reviews <= 200:
            return "MEDIUM"
        else:
            return "LOW"

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

            # Skip if we've seen this phone number (after cleaning)
            clean_phone = re.sub(r'[^\d]', '', lead.phone)
            if clean_phone and len(clean_phone) >= 10:
                # Use last 10 digits for comparison
                phone_key = clean_phone[-10:]
                if phone_key in seen_phones:
                    continue
                seen_phones.add(phone_key)

            # Skip if very similar name at same city
            name_key = f"{lead.name.lower().strip()}_{lead.city.lower().strip()}"
            if name_key in seen_names:
                continue

            # Mark as seen
            if lead.place_id:
                seen_ids.add(lead.place_id)
            seen_names.add(name_key)

            unique_leads.append(lead)

        return unique_leads

    @staticmethod
    def clean_leads(leads: List[Lead]) -> List[Lead]:
        """
        Full cleaning pipeline for leads.
        
        Steps:
        1. Standardize phone numbers
        2. Extract WhatsApp numbers
        3. Clean names (strip whitespace, fix casing)
        4. Clean addresses
        5. Assign priority scores
        6. Remove duplicates
        7. Sort by priority (HIGH first)
        """
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "IGNORE": 3}

        for lead in leads:
            # Standardize phone
            lead.phone = DataCleaner.standardize_phone(lead.phone)
            
            # Extract WhatsApp number from phone
            lead.whatsapp_number = DataCleaner.extract_whatsapp_number(lead.phone)
            
            # Clean name
            lead.name = lead.name.strip()
            
            # Clean address
            lead.address = lead.address.strip()
            
            # Clean city
            lead.city = lead.city.strip().title()
            
            # Clean category
            lead.category = lead.category.strip().title() if lead.category else "Other"
            
            # Assign priority based on website + reviews
            lead.priority = DataCleaner.assign_priority(lead)

        # Remove duplicates
        leads = DataCleaner.remove_duplicates(leads)

        # Sort by priority
        leads.sort(key=lambda l: priority_order.get(l.priority, 3))

        return leads

    @staticmethod
    def filter_leads(leads: List[Lead], include_with_website: bool = False) -> List[Lead]:
        """
        Filter leads based on criteria.
        
        Args:
            leads: List of leads to filter
            include_with_website: If False, removes businesses with websites
            
        Returns:
            Filtered list of leads
        """
        if include_with_website:
            return leads
        
        return [lead for lead in leads if lead.priority != "IGNORE"]
