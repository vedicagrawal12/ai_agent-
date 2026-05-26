from typing import List, Dict, Any, Optional
import os
import hashlib
from serpapi import GoogleSearch
from .base_collector import BaseCollector, Lead

class SerpApiCollector(BaseCollector):
    def __init__(self):
        pass

    @property
    def platform_name(self) -> str:
        return "SerpApi Google Maps"

    def search(self, query: str, city: str, max_results: int = 20, exclude_place_ids: set = None, start_offset: int = 0, api_key: str = None) -> List[Lead]:
        """
        Searches Google Maps using SerpApi.
        """
        api_key = api_key or os.getenv("SERPAPI_KEY")
        if not api_key:
            print("SERPAPI_KEY is not set.")
            return []
            
        search_query = f"{query} in {city}"
        
        leads = []
        start = start_offset
        
        # Max pagination safety limit to prevent infinite loop / consuming too many credits
        # 100 limit is standard for google_maps (5 pages)
        while len(leads) < max_results and start <= 100:
            params = {
                "engine": "google_maps",
                "q": search_query,
                "type": "search",
                "api_key": api_key,
                "start": start
            }
            
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                
                if "error" in results:
                    raise Exception(f"SerpApi Error: {results['error']}")
                    
                local_results = results.get("local_results", [])
                
                if not local_results:
                    break # No more results
                
                for place in local_results:
                    # SerpApi doesn't always provide place_id in local_results without extra calls,
                    # but it does provide a unique 'data_id' which we can use.
                    place_id = place.get("data_id") or place.get("place_id")
                    if not place_id:
                        # Generate a fallback ID from name+address to avoid conflicts
                        fallback = f"{place.get('title', '')}_{place.get('address', '')}_{city}"
                        place_id = f"serpapi_{hashlib.md5(fallback.encode()).hexdigest()[:12]}"
                    
                    # Exclude already saved place IDs if requested
                    if exclude_place_ids and place_id in exclude_place_ids:
                        continue
                    
                    # We need to structure this to match our existing Lead format
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
                        rating=float(place.get("rating") or 0),
                        reviews=int(place.get("reviews") or 0),
                        category=place.get("type", "Business"),
                        city=city,
                        source=self.platform_name
                    )
                    
                    # Check for phone numbers and valid data before adding
                    if lead.name:
                        leads.append(lead)
                    
                    if len(leads) >= max_results:
                        break
                
                # SerpApi usually returns 20 results per page
                start += 20
                        
            except Exception as e:
                print(f"Error fetching from SerpApi at start {start}: {e}")
                raise e
                
        return leads[:max_results]

    def get_details(self, place_id: str) -> Optional[Lead]:
        """
        Get detailed information. With SerpApi, we could do a 'place' search using the data_id,
        but for our current use case, the initial search returns enough data (phone, website).
        We'll just return None for now to satisfy the interface.
        """
        return None
