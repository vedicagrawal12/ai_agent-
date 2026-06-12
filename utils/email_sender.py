import os
import smtplib
import ssl
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def _get_smtp_config():
    """Retrieve SMTP settings from environment variables dynamically."""
    return {
        "host": os.getenv("SYSTEM_SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SYSTEM_SMTP_PORT", "465")),
        "email": os.getenv("SYSTEM_SMTP_EMAIL", ""),
        "password": os.getenv("SYSTEM_SMTP_PASSWORD", ""),
        "use_ssl": os.getenv("SYSTEM_SMTP_USE_SSL", "true").lower() == "true"
    }

def is_smtp_configured() -> bool:
    """Check if the system SMTP credentials are set up."""
    config = _get_smtp_config()
    return bool(config["email"] and config["password"])

def _send_smtp_email_sync(to_email: str, subject: str, html_body: str):
    """Synchronously send email using standard smtplib."""
    config = _get_smtp_config()
    
    if not config["email"] or not config["password"]:
        logger.warning(f"[Email Service] System SMTP credentials not configured. Skipping email to {to_email}.")
        return False
        
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"LeadHunter AI <{config['email']}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))
        
        # Setup connection (using SSL or TLS starttls)
        if config["use_ssl"]:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config["host"], config["port"], context=context, timeout=10) as server:
                server.login(config["email"], config["password"])
                server.sendmail(config["email"], to_email, msg.as_string())
        else:
            with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
                server.starttls()
                server.login(config["email"], config["password"])
                server.sendmail(config["email"], to_email, msg.as_string())
                
        logger.info(f"[Email Service] Successfully sent email to {to_email} with subject: '{subject}'")
        return True
    except Exception as e:
        logger.error(f"[Email Service] Failed to send email to {to_email}: {e}", exc_info=True)
        return False

def _run_in_background(target, *args):
    """Run a target function in a background daemon thread to avoid blocking the main server thread."""
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()

# --- Public Interface ---

def send_otp_email(to_email: str, otp: str):
    """Asynchronously send password reset verification OTP."""
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Reset Password OTP</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
                color: #334155;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }}
            .email-wrapper {{
                padding: 40px 20px;
                text-align: center;
            }}
            .email-card {{
                max-width: 500px;
                margin: 0 auto;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 40px 30px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.025);
                text-align: left;
            }}
            .header-logo {{
                font-size: 24px;
                font-weight: 800;
                color: #0284c7;
                margin-bottom: 25px;
                text-align: center;
            }}
            .title {{
                font-size: 20px;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 15px;
            }}
            .text {{
                font-size: 15px;
                line-height: 1.6;
                color: #475569;
                margin-bottom: 25px;
            }}
            .otp-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 32px;
                letter-spacing: 6px;
                font-weight: 800;
                color: #0369a1;
                background: #f0f9ff;
                border: 1px solid #b3e0ff;
                padding: 14px 28px;
                border-radius: 8px;
                display: inline-block;
                font-family: 'Courier New', Courier, monospace;
            }}
            .warning-text {{
                font-size: 13px;
                color: #64748b;
                border-top: 1px solid #f1f5f9;
                padding-top: 20px;
                margin-top: 30px;
                line-height: 1.5;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #94a3b8;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="email-card">
                <div class="header-logo">🎯 LeadHunter AI</div>
                <div class="title">Password Reset Verification Request</div>
                <div class="text">
                    Hello,<br><br>
                    We received a request to reset the password for your operator account on LeadHunter AI. Please use the following 6-digit One-Time Password (OTP) to proceed with security verification:
                </div>
                
                <div class="otp-container">
                    <div class="otp-code">{otp}</div>
                </div>
                
                <div class="text">
                    This OTP is single-use, highly confidential, and is <strong>valid for the next 10 minutes only</strong>.
                </div>
                
                <div class="warning-text">
                    <strong>Security Notice:</strong> If you did not initiate this request, you can safely ignore this email. Your password will remain unchanged and secure. Never share this OTP code with anyone.
                </div>
            </div>
            <div class="footer">
                © 2026 LeadHunter AI Security Console Team. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    _run_in_background(_send_smtp_email_sync, to_email, "LeadHunter AI Password Reset OTP", html_template)

def send_welcome_email(to_email: str, username: str):
    """Asynchronously send greeting onboarding email containing details about why LeadHunter, advantages, and instructions."""
    login_url = os.getenv("APP_URL", "http://localhost:5000/login")
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Welcome to LeadHunter AI</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
                color: #334155;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }}
            .email-wrapper {{
                padding: 40px 20px;
            }}
            .email-card {{
                max-width: 600px;
                margin: 0 auto;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.025);
            }}
            .header-logo {{
                font-size: 26px;
                font-weight: 800;
                color: #0284c7;
                margin-bottom: 25px;
                text-align: center;
            }}
            .title {{
                font-size: 22px;
                font-weight: 800;
                color: #0f172a;
                margin-bottom: 15px;
                border-bottom: 1px solid #f1f5f9;
                padding-bottom: 10px;
            }}
            .section-title {{
                font-size: 16px;
                font-weight: 700;
                color: #0369a1;
                margin-top: 30px;
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .text {{
                font-size: 15px;
                line-height: 1.6;
                color: #475569;
                margin-bottom: 15px;
            }}
            .advantage-list, .step-list {{
                padding-left: 20px;
                margin: 15px 0;
            }}
            .advantage-item, .step-item {{
                margin-bottom: 12px;
                font-size: 14.5px;
                line-height: 1.6;
                color: #475569;
            }}
            .highlight {{
                color: #0f172a;
                font-weight: 700;
            }}
            .btn-container {{
                text-align: center;
                margin: 35px 0 20px 0;
            }}
            .cta-button {{
                background: #0284c7;
                color: #ffffff !important;
                text-decoration: none;
                padding: 14px 30px;
                font-weight: 700;
                border-radius: 6px;
                display: inline-block;
                box-shadow: 0 4px 10px rgba(2, 132, 199, 0.2);
                transition: transform 0.2s ease;
            }}
            .footer {{
                margin-top: 40px;
                font-size: 12px;
                color: #94a3b8;
                text-align: center;
                border-top: 1px solid #f1f5f9;
                padding-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="email-card">
                <div class="header-logo">🎯 LeadHunter AI</div>
                <div class="title">Welcome to the Console, {username}! 🚀</div>
                
                <div class="text">
                    Hello and welcome! We are thrilled to have you join LeadHunter AI. Your agency client-scouting console is now fully active and ready to use.
                </div>
                
                <div class="section-title">Why LeadHunter AI?</div>
                <div class="text">
                    Manual client prospecting is slow, tedious, and highly repetitive. LeadHunter AI was engineered to automate the boring parts of lead generation—giving you the data, analytics, and custom cold pitches you need to land clients in a fraction of the time.
                </div>
                
                <div class="section-title">Key System Advantages</div>
                <ul class="advantage-list">
                    <li class="advantage-item"><span class="highlight">Automated Presence Auditing:</span> Instantly checks local business ratings, reviews, and website health to identify conversion weaknesses.</li>
                    <li class="advantage-item"><span class="highlight">Gemini Copywriter Integration:</span> Generates custom, tailored cold pitches matching local business profiles for services like Web Design, SEO, or Marketing.</li>
                    <li class="advantage-item"><span class="highlight">One-Click Multi-Channel Outreach:</span> Statelessly draft and send pitches immediately via zero-cost WhatsApp Web integration or SMTP servers.</li>
                </ul>
                
                <div class="section-title">How It Works (Step-by-Step)</div>
                <ol class="step-list">
                    <li class="step-item"><span class="highlight">Step 1 — Search:</span> Select a business category (e.g., "gym", "cafe") and city. Enable "Deep Scan" to let our robot scan multiple specific sub-locality zones.</li>
                    <li class="step-item"><span class="highlight">Step 2 — Audit:</span> Review rating gaps, filter out saved leads, and prioritize prospects that need immediate attention.</li>
                    <li class="step-item"><span class="highlight">Step 3 — Outreach:</span> Open the right-side details panel of any lead. Generate an AI cold pitch, customize parameters, and send it instantly.</li>
                </ol>
                
                <div class="btn-container">
                    <a href="{login_url}" class="cta-button">🚀 Access Client Console</a>
                </div>
                
                <div class="text" style="margin-top: 25px;">
                    We are dedicated to helping you scale your outreach. If you have any queries, feel free to contact our administrative team.
                </div>
                
                <div class="footer">
                    Warm regards,<br>
                    <strong>The LeadHunter AI Team</strong>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    _run_in_background(_send_smtp_email_sync, to_email, "Welcome to LeadHunter AI! 🚀", html_template)
