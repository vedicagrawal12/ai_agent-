import urllib.request
import re
import ssl
import socket
import ipaddress
import logging
from urllib.parse import urlparse

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
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
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
