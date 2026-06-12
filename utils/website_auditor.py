import time
import socket
import ipaddress
import requests
from html.parser import HTMLParser
import urllib.parse

class AuditHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.has_viewport = False
        self.h1_count = 0
        self.total_images = 0
        self.images_with_alt = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = {name.lower(): value for name, value in attrs}
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            content = attrs_dict.get("content", "")
            if name == "description":
                self.meta_description = content
            elif name == "viewport":
                self.has_viewport = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img":
            self.total_images += 1
            if "alt" in attrs_dict and attrs_dict["alt"].strip():
                self.images_with_alt += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data

def audit_website(url: str) -> dict:
    """
    Perform a lightweight SEO and performance audit on the given website URL.
    Returns a dictionary of scores, metrics, and list of recommendations.
    """
    if not url:
        return {}

    # Ensure URL has a scheme
    parsed_url = urllib.parse.urlparse(url)
    if not parsed_url.scheme:
        url = "http://" + url
        parsed_url = urllib.parse.urlparse(url)

    ssl_configured = parsed_url.scheme.lower() == "https"

    # SSRF protection — block requests to internal/private IPs
    _blocked_hosts = {'localhost', '127.0.0.1', '0.0.0.0', '::1', 'metadata.google.internal'}
    hostname = parsed_url.hostname
    if hostname:
        if hostname in _blocked_hosts:
            return {}
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(resolved_ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return {}
        except socket.gaierror:
            pass
    
    start_time = time.time()
    response_time = 9.99
    status_code = None
    html_content = ""
    error_msg = None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Fetch homepage content with a 5-second timeout
        response = requests.get(url, headers=headers, timeout=5)
        response_time = round(time.time() - start_time, 2)
        status_code = response.status_code
        html_content = response.text
    except requests.exceptions.SSLError:
        error_msg = "SSL Certificate Handshake Failed"
        ssl_configured = False
    except requests.exceptions.Timeout:
        error_msg = "Connection Timeout (took more than 5s)"
    except Exception as e:
        error_msg = f"Connection Failed: {str(e)}"

    # Parse HTML if successfully loaded
    parser = AuditHTMLParser()
    if html_content:
        try:
            parser.feed(html_content)
        except Exception:
            pass # Ignore html parsing issues, return whatever was found

    # 1. SSL/Security Score (10% weight)
    ssl_score = 100 if ssl_configured else 0

    # 2. Performance / Loading Speed Score (30% weight)
    if status_code is None or status_code >= 400:
        speed_score = 0
    elif response_time <= 1.0:
        speed_score = 100
    elif response_time <= 2.2:
        speed_score = 85
    elif response_time <= 4.0:
        speed_score = 60
    else:
        speed_score = 30

    # 3. Mobile Responsiveness Score (20% weight)
    mobile_score = 100 if parser.has_viewport else 0

    # 4. Image Alt Tags Score (10% weight)
    if parser.total_images == 0:
        alt_score = 100
    else:
        alt_score = int((parser.images_with_alt / parser.total_images) * 100)

    # 5. Core SEO Score (30% weight)
    seo_points = 0
    title_text = parser.title.strip()
    desc_text = parser.meta_description.strip()

    if title_text:
        seo_points += 35
        # Optimal title length check
        if 30 <= len(title_text) <= 60:
            seo_points += 5
            
    if desc_text:
        seo_points += 35
        # Optimal meta description length check
        if 120 <= len(desc_text) <= 160:
            seo_points += 5
            
    if parser.h1_count > 0:
        seo_points += 20

    seo_score = min(100, seo_points)

    # Calculate overall weighted score
    overall_score = int(
        (speed_score * 0.3) +
        (seo_score * 0.3) +
        (mobile_score * 0.2) +
        (ssl_score * 0.1) +
        (alt_score * 0.1)
    )

    # Generate recommendation items
    recommendations = []
    if not ssl_configured:
        recommendations.append({
            "type": "error",
            "category": "Security",
            "title": "SSL Missing or Inactive",
            "description": "Your website uses HTTP. Moving to HTTPS is a search engine ranking factor and secures visitor data."
        })
    if speed_score < 80:
        recommendations.append({
            "type": "warning",
            "category": "Speed",
            "title": f"Slow Load Time ({response_time}s)",
            "description": "Pages that take more than 2.5 seconds to load lose up to 40% of their prospective customers."
        })
    if not parser.has_viewport:
        recommendations.append({
            "type": "error",
            "category": "Mobile",
            "title": "Responsive Viewport Missing",
            "description": "No mobile viewport config found. Mobile responsiveness is required to rank on Google Mobile Search."
        })
    if not title_text:
        recommendations.append({
            "type": "error",
            "category": "SEO",
            "title": "Missing Page Title Tag",
            "description": "The title tag is the most critical HTML tag for search click-through optimization."
        })
    elif len(title_text) < 15 or len(title_text) > 70:
        recommendations.append({
            "type": "warning",
            "category": "SEO",
            "title": "Sub-optimal Title Tag Length",
            "description": f"Title tag has {len(title_text)} characters. Keep titles between 30 and 60 characters for best Google previews."
        })
    if not desc_text:
        recommendations.append({
            "type": "error",
            "category": "SEO",
            "title": "Missing Meta Description Tag",
            "description": "Without a description tag, Google will auto-generate search snippets which reduces organic clicks."
        })
    if parser.h1_count == 0:
        recommendations.append({
            "type": "warning",
            "category": "SEO",
            "title": "Missing H1 Heading tag",
            "description": "An H1 heading specifies the primary subject of the page and is a strong ranking signal."
        })
    elif parser.h1_count > 2:
        recommendations.append({
            "type": "warning",
            "category": "SEO",
            "title": "Multiple H1 tags found",
            "description": f"Found {parser.h1_count} H1 tags. Best practice is to use exactly one H1 per page to define the main theme."
        })
    if parser.total_images > 0 and alt_score < 70:
        recommendations.append({
            "type": "warning",
            "category": "SEO",
            "title": f"Missing Alt Tags ({parser.total_images - parser.images_with_alt} images)",
            "description": f"Only {alt_score}% of your site's images have descriptive alt attributes. Search robots rely on alt tags to index images."
        })

    return {
        "audited_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "overall_score": overall_score,
        "status_code": status_code,
        "error": error_msg,
        "metrics": {
            "response_time": response_time,
            "ssl_configured": ssl_configured,
            "has_viewport": parser.has_viewport,
            "title_length": len(title_text),
            "meta_description_length": len(desc_text),
            "h1_count": parser.h1_count,
            "total_images": parser.total_images,
            "images_with_alt": parser.images_with_alt
        },
        "scores": {
            "speed": speed_score,
            "seo": seo_score,
            "mobile": mobile_score,
            "ssl": ssl_score,
            "alt": alt_score
        },
        "recommendations": recommendations
    }
