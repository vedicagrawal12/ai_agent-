# Collectors package — extensible platform integrations
# Add new collectors here (e.g., instagram, facebook) in the future

from .base_collector import BaseCollector, Lead
from .serpapi_collector import SerpApiCollector

__all__ = ['BaseCollector', 'Lead', 'SerpApiCollector']
