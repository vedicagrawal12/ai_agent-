from typing import List, Dict, Any
import os
from serpapi import GoogleSearch
from .base_collector import BaseCollector, Lead

class SerpApiCollector(BaseCollector):
    def __init__(self):
        pass

    @property
    def platform_name(self) -> str:
        return "SerpApi Google Maps"

    def search(self, query: str, city: str, max_results: int = 20) -> List[Lead]:
        """
        Searches Google Maps using SerpApi.
        """
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            print("SERPAPI_KEY is not set.")
            return []
            
        search_query = f"{query} in {city}"
        
        params = {
            "engine": "google_maps",
            "q": search_query,
            "type": "search",
            "api_key": api_key
        }
        
        leads = []
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])
            
            for place in local_results:
                # SerpApi doesn't always provide place_id in local_results without extra calls,
                # but it does provide a unique 'data_id' which we can use.
                place_id = place.get("data_id") or place.get("place_id") or place.get("title")
                
                # We need to structure this to match our existing Lead format
                # Note: SerpApi might not always return website natively in 'search' type without 'place' details,
                # but sometimes it provides links. We'll extract what we can.
                website = ""
                links = place.get("links", {})
                if links:
                    website = links.get("website", "")
                
                if not website:
                    website = place.get("website", "")
                
                lead = Lead(
                    place_id=place_id,
                    name=place.get("title", ""),
                    phone=place.get("phone", ""),
                    address=place.get("address", ""),
                    website=website,
                    rating=place.get("rating", 0.0),
                    reviews=place.get("reviews", 0),
                    category=place.get("type", "Business"),
                    city=city,
                    source=self.platform_name
                )
                
                # Check for phone numbers and valid data before adding
                if lead.name:
                    leads.append(lead)
                
                if len(leads) >= max_results:
                    break
                    
        except Exception as e:
            print(f"Error fetching from SerpApi: {e}")
            
        return leads

    def get_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information. With SerpApi, we could do a 'place' search using the data_id,
        but for our current use case, the initial search returns enough data (phone, website).
        We'll just return an empty dict for now to satisfy the interface.
        """
        return {}
