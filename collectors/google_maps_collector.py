"""
Google Maps Collector — Extracts business leads from Google Places API (New).

⚠️  DEPRECATED / UNUSED: This collector is NOT used anywhere in the application.
    The app uses SerpApiCollector instead. This module requires a separate Google
    Cloud Platform API key (not the SerpApi key). Kept for potential future use.

Uses the official Google Places API Text Search endpoint to find businesses,
then fetches detailed information for each result including phone numbers,
addresses, websites, ratings, and reviews.
"""

import requests
import time
import re
from typing import List, Optional
from .base_collector import BaseCollector, Lead


class GoogleMapsCollector(BaseCollector):
    """
    Collector that searches Google Maps via the Places API (New).
    
    Requires a valid Google Places API key with the Places API (New) enabled.
    """

    # Google Places API endpoints
    TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
    PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

    # Fields to request from the API
    SEARCH_FIELD_MASK = ",".join([
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.websiteUri",
        "places.internationalPhoneNumber",
        "places.nationalPhoneNumber",
        "places.primaryTypeDisplayName",
        "places.businessStatus",
        "places.primaryType"
    ])

    DETAILS_FIELD_MASK = ",".join([
        "id",
        "displayName",
        "formattedAddress",
        "rating",
        "userRatingCount",
        "websiteUri",
        "internationalPhoneNumber",
        "nationalPhoneNumber",
        "primaryTypeDisplayName",
        "businessStatus",
        "primaryType"
    ])

    def __init__(self, api_key: str):
        """Initialize with Google Places API key."""
        self.api_key = api_key

    @property
    def platform_name(self) -> str:
        return "Google Maps"

    def _get_headers(self, field_mask: str) -> dict:
        """Build request headers with API key and field mask."""
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask
        }

    def _extract_city(self, address: str) -> str:
        """
        Extract city name from a formatted address string.
        
        Handles Indian address formats like:
        - "123, MG Road, Bhopal, Madhya Pradesh 462001, India"
        - "Shop 5, Mall Road, New Delhi, Delhi 110001, India"
        """
        if not address:
            return ""
        
        # Split by comma and work backwards (city is usually 3rd or 4th from end)
        parts = [p.strip() for p in address.split(",")]
        
        if len(parts) >= 3:
            # Try to find the city — usually before the state
            for i in range(len(parts) - 1, -1, -1):
                part = parts[i].strip()
                # Skip country, state with pincode, and very short parts
                if part.lower() in ["india", "भारत"]:
                    continue
                # Skip parts with pincode (contain numbers at end)
                if re.search(r'\d{6}', part):
                    continue
                # This should be the city
                # Clean any remaining numbers
                city = re.sub(r'\d+', '', part).strip()
                if city and len(city) > 1:
                    return city
        
        # Fallback: return the 2nd-to-last part if available
        if len(parts) >= 2:
            return parts[-2].strip()
        
        return address

    def _format_phone_for_whatsapp(self, phone: str) -> str:
        """
        Format phone number for WhatsApp (remove spaces, dashes, add country code).
        
        Converts various formats to WhatsApp-compatible format:
        - "+91 98765 43210" → "919876543210"
        - "098765 43210" → "919876543210"
        - "9876543210" → "919876543210"
        """
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Remove leading +
        cleaned = cleaned.lstrip('+')
        
        # If starts with 91 and has 12 digits, it's already Indian format
        if cleaned.startswith('91') and len(cleaned) == 12:
            return cleaned
        
        # If starts with 0, remove it and add 91
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        
        # If it's 10 digits (Indian local number), add 91
        if len(cleaned) == 10:
            cleaned = '91' + cleaned
        
        return cleaned

    def _calculate_priority(self, has_website: bool, review_count: int) -> str:
        """
        Calculate lead priority based on online presence.
        
        Priority logic:
        - Has website → IGNORE (they already have online presence)
        - No website + <50 reviews → HIGH (most in need of help)
        - No website + 50-200 reviews → MEDIUM (growing but need web presence)
        - No website + >200 reviews → LOW (established but no website)
        """
        if has_website:
            return "IGNORE"
        
        if review_count < 50:
            return "HIGH"
        elif review_count <= 200:
            return "MEDIUM"
        else:
            return "LOW"

    def _parse_place(self, place_data: dict, search_city: str = "") -> Lead:
        """
        Parse a Google Places API response into a Lead object.
        
        Args:
            place_data: Raw place data from the API
            search_city: The city that was searched for (fallback)
            
        Returns:
            Lead object with all extracted details
        """
        name = place_data.get("displayName", {}).get("text", "Unknown")
        address = place_data.get("formattedAddress", "")
        phone = place_data.get("internationalPhoneNumber", "") or place_data.get("nationalPhoneNumber", "")
        website = place_data.get("websiteUri", "")
        rating = place_data.get("rating", 0.0)
        reviews = place_data.get("userRatingCount", 0)
        category = place_data.get("primaryTypeDisplayName", {}).get("text", "") or place_data.get("primaryType", "")
        place_id = place_data.get("id", "")
        business_status = place_data.get("businessStatus", "")

        # Extract city from address, fallback to search city
        city = self._extract_city(address) or search_city

        # Calculate priority
        has_website = bool(website and website.strip())
        priority = self._calculate_priority(has_website, reviews)

        # Format WhatsApp number
        whatsapp_number = self._format_phone_for_whatsapp(phone)

        return Lead(
            name=name,
            phone=phone,
            address=address,
            website=website,
            rating=round(rating, 1) if rating is not None else 0.0,
            reviews=reviews or 0,
            category=category,
            city=city,
            priority=priority,
            whatsapp_number=whatsapp_number,
            place_id=place_id,
            source="google_maps"
        )

    def search(self, query: str, city: str, max_results: int = 20, exclude_place_ids: set = None, start_offset: int = 0, api_key: str = None) -> List[Lead]:
        """
        Search Google Maps for businesses matching the query in the given city.
        
        Args:
            query: Business type (e.g., "gym", "salon", "restaurant")
            city: City name (e.g., "bhopal", "delhi")
            max_results: Maximum results to return (API max is 20 per page)
            exclude_place_ids: Optional set of place IDs to exclude (unused, for interface compat)
            start_offset: Starting offset for pagination (unused, for interface compat)
            api_key: Optional override API key (falls back to self.api_key)
            
        Returns:
            List of Lead objects with full business details
        """
        # Use provided api_key or fall back to instance key
        effective_api_key = api_key or self.api_key
        # Build the search query
        search_query = f"{query} in {city}"

        headers = self._get_headers(self.SEARCH_FIELD_MASK)
        payload = {
            "textQuery": search_query,
            "pageSize": min(max_results, 20),  # API max is 20 per page
            "languageCode": "en"
        }

        try:
            response = requests.post(
                self.TEXT_SEARCH_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Bad request")
                raise Exception(f"API Error: {error_msg}")

            if response.status_code == 403:
                raise Exception("Invalid API key or Places API not enabled. Please check your Google Cloud Console.")

            if response.status_code == 429:
                raise Exception("API rate limit exceeded. Please wait a moment and try again.")

            response.raise_for_status()
            data = response.json()

            places = data.get("places", [])
            leads = []

            for place_data in places:
                # Simulate human-like browsing — small delay between processing
                time.sleep(0.1)
                
                lead = self._parse_place(place_data, city)
                
                # Only include operational businesses
                business_status = place_data.get("businessStatus", "")
                if business_status and business_status != "OPERATIONAL":
                    continue

                leads.append(lead)

            # Handle pagination — get next page if available and we need more results
            next_page_token = data.get("nextPageToken")
            while next_page_token and len(leads) < max_results:
                # Google requires a short delay before using page token
                time.sleep(2)
                
                payload["pageToken"] = next_page_token
                response = requests.post(
                    self.TEXT_SEARCH_URL,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                for place_data in data.get("places", []):
                    time.sleep(0.1)
                    lead = self._parse_place(place_data, city)
                    business_status = place_data.get("businessStatus", "")
                    if business_status and business_status != "OPERATIONAL":
                        continue
                    leads.append(lead)
                
                next_page_token = data.get("nextPageToken")

            return leads[:max_results]

        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Google API. Please check your internet connection.")
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

    def get_details(self, place_id: str) -> Optional[Lead]:
        """
        Get detailed information for a specific place by its ID.
        
        Args:
            place_id: Google Places place ID
            
        Returns:
            Lead object with full details, or None if not found
        """
        url = self.PLACE_DETAILS_URL.format(place_id=place_id)
        headers = self._get_headers(self.DETAILS_FIELD_MASK)

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._parse_place(data)
        except Exception:
            return None
