import requests
import re
from urllib.parse import urljoin, urlparse

class EmailScraper:
    """Robust utility to extract public business email addresses from websites."""
    
    EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # Exclude common false positives and static assets
    EXCLUDE_PATTERNS = [
        r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.svg$', r'\.webp$',
        r'\.css$', r'\.js$', r'\.mp4$', r'\.woff$', r'\.woff2$', r'\.ttf$',
        r'^sentry@', r'^bootstrap@', r'^jquery@', r'^example@', r'^yourname@',
        r'^email@', r'^user@', r'^domain@', r'^test@'
    ]

    @classmethod
    def clean_email(cls, email: str) -> str:
        """Clean extra dots or weird characters from re-grouped email extraction."""
        email = email.strip().lower()
        # Remove trailing periods
        if email.endswith('.'):
            email = email[:-1]
        return email

    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Check if the parsed email is a legitimate contact email (and not a false positive static resource)."""
        email = cls.clean_email(email)
        
        # Check if matches any excluded pattern
        for pattern in cls.EXCLUDE_PATTERNS:
            if re.search(pattern, email):
                return False
                
        # Must have a valid structure
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return False
            
        return True

    @classmethod
    def scrape_emails_from_url(cls, url: str) -> list:
        """
        Scrape public emails from a given webpage URL.
        Includes safety timeouts and user-agents.
        """
        if not url:
            return []
            
        # Standardize URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        try:
            print(f"Fetching website for email scraping: {url}...")
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                print(f"Failed to fetch {url} - Status: {response.status_code}")
                return []
                
            html_content = response.text
            found_emails = re.findall(cls.EMAIL_REGEX, html_content)
            
            valid_emails = []
            for email in found_emails:
                cleaned = cls.clean_email(email)
                if cls.is_valid_email(cleaned) and cleaned not in valid_emails:
                    valid_emails.append(cleaned)
                    
            return valid_emails
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []

    @classmethod
    def deep_scrape_business_emails(cls, main_url: str) -> str:
        """
        Main entry point for pro-level business email scraping:
        1. Scrapes the home page.
        2. If no email found, searches homepage HTML for common contact page links.
        3. Scrapes found contact pages.
        4. Returns the single best found email address, or empty string.
        """
        if not main_url:
            return ""
            
        # Step 1: Scrape Home Page
        emails = cls.scrape_emails_from_url(main_url)
        if emails:
            print(f"Found emails on home page: {emails}")
            return emails[0]
            
        # Step 2: Try to discover and scrape Contact Pages
        try:
            main_url = main_url.strip()
            if not main_url.startswith(('http://', 'https://')):
                main_url = 'https://' + main_url
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            res = requests.get(main_url, headers=headers, timeout=5)
            if res.status_code != 200:
                return ""
                
            # Regex to find links containing "contact", "about", or "support"
            links = re.findall(r'href=["\'](https?://[^\s"\'>]+|/[^\s"\'>]+)["\']', res.text)
            
            contact_links = set()
            for link in links:
                lower_link = link.lower()
                if any(x in lower_link for x in ['contact', 'about-us', 'contact-us', 'support']):
                    # Resolve relative URLs
                    full_link = urljoin(main_url, link)
                    # Stay on the same domain
                    if urlparse(full_link).netloc == urlparse(main_url).netloc:
                        contact_links.add(full_link)
            
            # If no contact links found in HTML, try guessing relative paths
            if not contact_links:
                for path in ['/contact', '/contact-us', '/about']:
                    contact_links.add(urljoin(main_url, path))
                    
            print(f"Discovered contact paths to deep scan: {contact_links}")
            
            # Step 3: Deep Scan Contact Pages
            for contact_url in list(contact_links)[:3]: # limit to top 3 links to save time
                try:
                    c_emails = cls.scrape_emails_from_url(contact_url)
                    if c_emails:
                        print(f"Found emails on contact page {contact_url}: {c_emails}")
                        return c_emails[0]
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Deep scraping error: {e}")
            
        return ""
