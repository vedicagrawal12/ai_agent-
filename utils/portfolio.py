import urllib.request
import urllib.error
import re
import ssl
import socket
import ipaddress
import logging
from urllib.parse import urlparse

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Perform security validation of the new URL
        if not PortfolioParser._is_safe_url(newurl):
            raise urllib.error.HTTPError(req.full_url, code, f"Redirect to unsafe URL blocked: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class PortfolioParser:
    BLOCKED_HOSTNAMES = {'localhost', '127.0.0.1', '0.0.0.0', '::1', 'metadata.google.internal'}

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """SSRF protection — block requests to internal/private IPs."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
            if hostname in PortfolioParser.BLOCKED_HOSTNAMES:
                logging.warning(f"[SSRF Block] Blocked portfolio request to internal hostname: {hostname}")
                return False
            try:
                resolved_ip = socket.gethostbyname(hostname)
                ip_obj = ipaddress.ip_address(resolved_ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                    logging.warning(f"[SSRF Block] Blocked portfolio request to private IP: {hostname} -> {resolved_ip}")
                    return False
            except socket.gaierror:
                pass
            return True
        except Exception:
            return False

    @staticmethod
    def fetch_and_parse(url: str) -> list:
        """
        Fetches the portfolio page and parses out all project cards.
        """
        # Clean URL
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        # SSRF protection
        if not PortfolioParser._is_safe_url(url):
            raise Exception("URL targets an internal or private network address. Request blocked for security.")

        try:
            # Setup request with a user-agent to bypass basic blocks
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            # Try with secure SSL verification (BUG-M8)
            ctx = ssl.create_default_context()
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), SafeRedirectHandler())
            with opener.open(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                
            return PortfolioParser.parse_html(html)
        except Exception as e:
            logging.error(f"Error fetching portfolio from {url}: {e}")
            raise Exception(f"Failed to fetch portfolio: {str(e)}")

    @staticmethod
    def parse_html(html: str) -> list:
        projects = []
        # Split by project-card class
        parts = html.split('class="project-card')
        
        for part in parts[1:]:  # Skip the first part before any project card
            try:
                # 1. Title is in <h3>...</h3>
                h3_start = part.find('<h3>')
                if h3_start == -1:
                    continue
                h3_end = part.find('</h3>', h3_start)
                title = part[h3_start + 4:h3_end].strip()
                title = title.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                
                # 2. Tech stack is in class="tech-stack">...<
                tech_start = part.find('class="tech-stack"')
                tech = ""
                if tech_start != -1:
                    inner_start = part.find('>', tech_start)
                    inner_end = part.find('<', inner_start)
                    tech = part[inner_start + 1:inner_end].strip()
                    tech = tech.replace('&amp;', '&')
                    
                # 3. Description is in class="project-desc">...<
                desc_start = part.find('class="project-desc"')
                desc = ""
                if desc_start != -1:
                    inner_start = part.find('>', desc_start)
                    inner_end = part.find('</p>', inner_start)
                    desc = part[inner_start + 1:inner_end].strip()
                    # Clean html tags inside description
                    desc = re.sub('<[^<]+?>', '', desc)
                    desc = desc.replace('&amp;', '&').replace('&nbsp;', ' ').strip()
                    
                # 4. Live demo link
                demo_url = ""
                links_part_start = part.find('class="project-links"')
                if links_part_start != -1:
                    links_part_end = part.find('</div>', links_part_start)
                    links_section = part[links_part_start:links_part_end]
                    
                    # Find all a tags
                    a_tags = re.findall(r'<a\s+[^>]*href=["\'](.*?)["\'](.*?)</a>', links_section, re.S)
                    for href, rest in a_tags:
                        rest_clean = re.sub('<[^<]+?>', '', rest).lower()
                        if "live demo" in rest_clean or "live" in rest_clean or "demo" in rest_clean or "external-link" in rest_clean:
                            demo_url = href
                            break
                    
                    # Fallback if no explicit live demo text, take the first link that is not github and not empty/#
                    if not demo_url:
                        for href, rest in a_tags:
                            href_lower = href.lower()
                            if "github.com" not in href_lower and href != "#" and href.strip():
                                demo_url = href
                                break
                
                projects.append({
                    "title": title,
                    "tech": tech,
                    "desc": desc,
                    "demo_url": demo_url
                })
            except Exception as err:
                logging.warning(f"Error parsing card chunk: {err}")
                
        return projects

def get_best_matching_project(category: str, name: str, projects: list) -> tuple:
    """
    Finds the best matching project for the lead's category/name.
    If no match is found, fallback to the first project in the list as requested.
    Returns (matched_project, other_projects)
    """
    if not projects:
        return None, []
        
    category_lower = (category or "").lower()
    name_lower = (name or "").lower()
    search_text = f"{category_lower} {name_lower}"
    
    # Fuzzy keyword mapping covering multiple industry verticals
    category_keyword_map = [
        { "keywords": ['gym', 'fitness', 'yoga', 'crossfit', 'workout', 'pilates', 'boxing', 'zumba', 'martial'], "project_keywords": ['gym', 'fitness', 'workout', 'health'] },
        { "keywords": ['dentist', 'dental', 'clinic', 'doctor', 'hospital', 'dermatolog', 'physician', 'ortho', 'eye', 'physio', 'chiro', 'ayurved', 'pharma', 'patholog', 'diagnostic'], "project_keywords": ['clinic', 'doctor', 'hospital', 'health', 'medical', 'dental', 'care'] },
        { "keywords": ['salon', 'spa', 'parlour', 'parlor', 'barber', 'beauty', 'nail', 'hair', 'makeup', 'grooming', 'skincare', 'tattoo', 'mehndi', 'bridal'], "project_keywords": ['salon', 'beauty', 'spa', 'barber', 'grooming', 'style'] },
        { "keywords": ['restaurant', 'cafe', 'hotel', 'bakery', 'bar', 'dhaba', 'food', 'dine', 'dining', 'catering', 'sweet', 'pizza', 'biryani', 'juice', 'tea', 'coffee', 'lounge', 'pub', 'banquet', 'resort', 'prandium'], "project_keywords": ['hotel', 'restaurant', 'cafe', 'food', 'dining', 'prandium', 'bakery', 'catering'] },
        { "keywords": ['school', 'coaching', 'tutor', 'academy', 'institute', 'training', 'education', 'college', 'preschool', 'playschool', 'nursery', 'classes', 'learning'], "project_keywords": ['school', 'education', 'academy', 'learning', 'coaching', 'course', 'training'] },
        { "keywords": ['garage', 'car wash', 'mechanic', 'automobile', 'auto', 'bike', 'vehicle', 'tyre', 'car dealer', 'showroom', 'service center'], "project_keywords": ['auto', 'car', 'vehicle', 'garage', 'mechanic', 'bike'] },
        { "keywords": ['builder', 'property', 'real estate', 'architect', 'interior', 'construction', 'contractor', 'developer', 'flat', 'apartment', 'villa'], "project_keywords": ['property', 'real estate', 'construction', 'builder', 'architect', 'interior', 'home'] },
        { "keywords": ['lawyer', 'advocate', 'legal', 'chartered', 'accountant', 'tax', 'consultant', 'financial', 'insurance', 'loan', 'investment'], "project_keywords": ['lawyer', 'legal', 'finance', 'accounting', 'consulting', 'tax'] },
        { "keywords": ['pet ', 'pets', 'veterinary', 'vet ', 'animal', 'dog ', 'dogs', 'puppy', 'kitten', 'kennel', 'aquarium'], "project_keywords": ['pet', 'vet', 'animal', 'dog'] },
        { "keywords": ['shop', 'store', 'boutique', 'electronics', 'furniture', 'jewel', 'clothing', 'garment', 'fashion', 'textile', 'gift', 'handicraft', 'grocery', 'supermarket', 'kirana'], "project_keywords": ['shop', 'store', 'ecommerce', 'boutique', 'retail', 'fashion', 'product'] },
        { "keywords": ['photographer', 'photography', 'wedding', 'event', 'planner', 'dj', 'decoration', 'florist', 'caterer', 'videograph', 'studio', 'music', 'band'], "project_keywords": ['photo', 'wedding', 'event', 'studio', 'portfolio', 'creative', 'film'] },
        { "keywords": ['plumber', 'electrician', 'painter', 'pest control', 'ac repair', 'cleaning', 'laundry', 'packers', 'movers', 'carpenter', 'locksmith', 'solar', 'cctv', 'security'], "project_keywords": ['service', 'repair', 'cleaning', 'home', 'maintenance'] },
        { "keywords": ['travel', 'tour', 'taxi', 'cab', 'courier', 'logistics', 'transport', 'bus', 'flight', 'visa', 'rental'], "project_keywords": ['travel', 'tour', 'booking', 'trip', 'transport', 'cab'] },
        { "keywords": ['hostel', 'pg', 'paying guest', 'stay', 'accommodation', 'lodge', 'guest house', 'homestay', 'dormitory'], "project_keywords": ['hostel', 'buddy', 'stay', 'accommodation', 'booking', 'room'] }
    ]
    
    matched_project = None
    other_projects = []
    
    # 1. Try to find a group match
    matched_group = None
    for group in category_keyword_map:
        if any(kw in search_text for kw in group["keywords"]):
            matched_group = group
            break
            
    if matched_group:
        for p in projects:
            p_text = f"{p.get('title', '')} {p.get('desc', '')}".lower()
            if any(kw in p_text for kw in matched_group["project_keywords"]):
                matched_project = p
                break
                
    # 2. Fallback: if no category match is found, select the first project in the portfolio list
    if not matched_project and projects:
        matched_project = projects[0]
        
    # Helper to parse tech tag lists for all returned projects
    for p in projects:
        tech = p.get('tech', '')
        p['tech_tags'] = [t.strip() for t in tech.split(',') if t.strip()] if tech else []
        
    # Compile other projects list
    if matched_project:
        other_projects = [p for p in projects if p != matched_project]
    else:
        other_projects = projects
        
    return matched_project, other_projects

