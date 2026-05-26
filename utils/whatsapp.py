"""
WhatsApp Messenger — Generate personalized WhatsApp messages and links.

Uses the wa.me URL scheme to open WhatsApp with pre-filled messages.
Supports message templates with variable substitution for personalization.
"""

import urllib.parse
from typing import Dict, List
from collectors.base_collector import Lead


class WhatsAppMessenger:
    """
    Builds personalized WhatsApp messages for outreach.
    
    Uses wa.me links which work on both mobile and desktop WhatsApp.
    """

    # Default message templates
    DEFAULT_TEMPLATES = {
        "website_pitch": {
            "name": "Website Service Pitch",
            "message": (
                "Hello {business_name}! 👋\n\n"
                "I noticed your business in {city} and I'm impressed by your {rating}⭐ rating "
                "with {reviews} reviews on Google Maps.\n\n"
                "I specialize in creating professional websites for local businesses like yours. "
                "{project_sample}\n\n"
                "A website can help you:\n"
                "✅ Get found online by more customers\n"
                "✅ Showcase your services & prices\n"
                "✅ Accept online bookings/inquiries\n"
                "✅ Build trust with a professional online presence\n\n"
                "I'd love to discuss how I can help {business_name} grow online. "
                "Would you be interested in a free consultation?\n\n"
                "Looking forward to hearing from you! 🙏"
            )
        },
        "digital_presence": {
            "name": "Digital Presence Pitch",
            "message": (
                "Hi {business_name}! 🙏\n\n"
                "I came across your {category} business in {city} and wanted to reach out.\n\n"
                "In today's digital world, having a strong online presence is essential. "
                "{project_sample}\n\n"
                "I help local businesses like yours get:\n\n"
                "🌐 A professional website\n"
                "📱 Social media management\n"
                "📍 Better Google Maps visibility\n"
                "📈 More customer inquiries\n\n"
                "Would you like to know more? I offer a free initial consultation.\n\n"
                "Best regards! 😊"
            )
        },
        "simple_intro": {
            "name": "Simple Introduction",
            "message": (
                "Hello {business_name}! 👋\n\n"
                "I help local businesses in {city} build their online presence. "
                "{project_sample}\n\n"
                "Would you be interested in a free website consultation?\n\n"
                "Thank you! 🙏"
            )
        },
        "custom": {
            "name": "Custom Message",
            "message": ""
        }
    }

    @staticmethod
    def get_templates() -> Dict:
        """Return all available message templates."""
        return {
            key: {
                "name": template["name"],
                "message": template["message"]
            }
            for key, template in WhatsAppMessenger.DEFAULT_TEMPLATES.items()
        }

    @staticmethod
    def build_message(template_key: str, lead: Lead, custom_message: str = "") -> str:
        """
        Build a personalized message from a template and lead data.
        
        Available template variables:
        - {business_name} — Name of the business
        - {city} — City of the business
        - {category} — Business category
        - {rating} — Google Maps rating
        - {reviews} — Number of reviews
        - {address} — Full address
        - {phone} — Phone number
        
        Args:
            template_key: Key of the template to use
            lead: Lead object with business details
            custom_message: Custom message text (used when template_key is "custom")
            
        Returns:
            Personalized message string
        """
        if template_key == "custom":
            message = custom_message
        else:
            template = WhatsAppMessenger.DEFAULT_TEMPLATES.get(template_key)
            if not template:
                raise ValueError(f"Unknown template: {template_key}")
            message = template["message"]

        # Replace template variables
        message = message.replace("{business_name}", lead.name or "there")
        message = message.replace("{city}", lead.city or "your city")
        message = message.replace("{category}", lead.category or "business")
        message = message.replace("{rating}", str(lead.rating or "great"))
        message = message.replace("{reviews}", str(lead.reviews if lead.reviews is not None else "many"))
        message = message.replace("{address}", lead.address or "")
        message = message.replace("{phone}", lead.phone or "")
        # Remove project_sample placeholder — only used in AI-generated pitches
        message = message.replace(" {project_sample}", "").replace("{project_sample}", "")
        # Clean any double whitespace/spaces left from removed placeholders
        import re
        message = re.sub(r'[ \t]+', ' ', message)  # Remove multiple spaces
        message = re.sub(r' \n', '\n', message)  # Remove space before newline
        message = re.sub(r'\n\s*\n\s*\n', '\n\n', message)
        message = message.strip()

        return message

    @staticmethod
    def generate_whatsapp_link(phone_number: str, message: str) -> str:
        """
        Generate a WhatsApp link with pre-filled message using official send API.
        
        Args:
            phone_number: Phone number in international format (digits only, e.g. "919876543210")
            message: Pre-filled message text
            
        Returns:
            WhatsApp URL string (e.g., "https://api.whatsapp.com/send?phone=919876543210&text=Hello...")
        """
        if not phone_number:
            return ""
        
        # Clean phone number — digits only
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # URL-encode the message
        encoded_message = urllib.parse.quote(message)
        
        return f"https://api.whatsapp.com/send?phone={clean_number}&text={encoded_message}"

    @staticmethod
    def generate_bulk_links(leads: List[Lead], template_key: str, custom_message: str = "") -> List[Dict]:
        """
        Generate WhatsApp links for multiple leads.
        
        Args:
            leads: List of Lead objects
            template_key: Template to use for messages
            custom_message: Custom message (when template_key is "custom")
            
        Returns:
            List of dicts with lead info and WhatsApp link
        """
        results = []
        
        for lead in leads:
            if not lead.whatsapp_number:
                continue
            
            message = WhatsAppMessenger.build_message(template_key, lead, custom_message)
            link = WhatsAppMessenger.generate_whatsapp_link(lead.whatsapp_number, message)
            
            results.append({
                "name": lead.name,
                "phone": lead.phone,
                "whatsapp_number": lead.whatsapp_number,
                "whatsapp_link": link,
                "message_preview": message[:100] + "..." if len(message) > 100 else message
            })
        
        return results
