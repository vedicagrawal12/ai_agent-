"""
Base Collector — Abstract interface for all platform collectors.

To add a new platform (e.g., Instagram, Facebook), create a new file
in the collectors/ directory and inherit from BaseCollector.

Example:
    class InstagramCollector(BaseCollector):
        def search(self, query, city):
            # Implement Instagram business search logic
            pass
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Lead:
    """Represents a single business lead."""
    name: str
    phone: str = ""
    address: str = ""
    website: str = ""
    rating: float = 0.0
    reviews: int = 0
    category: str = ""
    city: str = ""
    priority: str = "LOW"  # HIGH, MEDIUM, LOW, IGNORE
    whatsapp_number: str = ""
    place_id: str = ""
    source: str = "google_maps"  # Track which platform the lead came from
    instagram: str = ""
    facebook: str = ""
    is_broken_website: int = 0
    line_type: str = ""

    def to_dict(self):
        return asdict(self)


class BaseCollector(ABC):
    """
    Abstract base class for all platform collectors.
    
    Every collector must implement the `search` method that returns
    a list of Lead objects. This makes the system extensible —
    just add a new collector class for each new platform.
    
    Future collectors to add:
    - InstagramCollector: Search Instagram for local businesses
    - FacebookCollector: Search Facebook Pages for local businesses
    - JustDialCollector: Search JustDial for Indian local businesses
    - IndiaMartCollector: Search IndiaMart for business leads
    """

    @abstractmethod
    def search(self, query: str, city: str, max_results: int = 20, exclude_place_ids: set = None, start_offset: int = 0, api_key: str = None) -> List[Lead]:
        """
        Search for businesses on the platform.
        
        Args:
            query: Business type/keyword (e.g., "gym", "salon")
            city: City name (e.g., "bhopal", "delhi")
            max_results: Maximum number of results to return
            exclude_place_ids: Optional set of place IDs to exclude from search results
            start_offset: Starting offset (pagination start index) for the search
            api_key: Optional API key to use for the platform search
            
        Returns:
            List of Lead objects with business details
        """
        pass

    @abstractmethod
    def get_details(self, place_id: str) -> Optional[Lead]:
        """
        Get detailed information for a specific business.
        
        Args:
            place_id: Unique identifier for the business on this platform
            
        Returns:
            Lead object with full details, or None if not found
        """
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the name of the platform (e.g., 'Google Maps')."""
        pass
