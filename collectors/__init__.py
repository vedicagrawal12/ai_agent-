# Collectors package — extensible platform integrations
# Add new collectors here (e.g., instagram, facebook) in the future

from .base_collector import BaseCollector, Lead
from .google_maps_collector import GoogleMapsCollector
from .serpapi_collector import SerpApiCollector

__all__ = ['BaseCollector', 'Lead', 'GoogleMapsCollector', 'SerpApiCollector']
