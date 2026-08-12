"""
SMTP Email Sender for Stremly Cold Outreach.
Handles TLS/SSL connections, MIME alternative formatting, and secure delivery via Gmail SMTP.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import (
    SENDER_EMAIL,
    SENDER_NAME,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_SERVER,
    SMTP_PORT
)

logger = logging.getLogger(__name__)

def test_smtp_connection(username=None, password=None, server=None, port=None):
    """Verify SMTP connection and authentication credentials."""
    user = username or SMTP_USERNAME
    pwd = password or SMTP_PASSWORD
    host = server or SMTP_SERVER
    p = port or SMTP_PORT

    if not user or not pwd:
        return {"success": False, "error": "Missing SMTP username or password"}

    try:
        if p == 465:
            smtp = smtplib.SMTP_SSL(host, p, timeout=10)
        else:
            smtp = smtplib.SMTP(host, p, timeout=10)
            smtp.starttls()
            
        smtp.login(user, pwd)
        smtp.quit()
        return {"success": True, "message": "SMTP connection successful"}
    except Exception as e:
        logger.error(f"SMTP Connection Test Failed: {e}")
        return {"success": False, "error": str(e)}

def send_outreach_email(recipient_email, subject, html_body, text_body, sender_email=None, sender_name=None):
    """
    Sends a cold outreach email using MIMEMultipart('alternative').
    
    Headers:
      From: SENDER_NAME <SENDER_EMAIL>
      Reply-To: SENDER_EMAIL
      To: recipient_email
    """
    from_email = sender_email or SENDER_EMAIL or SMTP_USERNAME
    from_name = sender_name or SENDER_NAME or "Stremly"

    if not recipient_email or "@" not in recipient_email:
        return {"success": False, "error": f"Invalid recipient email address: '{recipient_email}'"}

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return {"success": False, "error": "SMTP credentials not configured in environment (.env)"}

    # Construct MIMEMultipart alternative message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = recipient_email
    msg["Reply-To"] = from_email

    # Attach Plain-Text first, then HTML (MIME standard priority)
    part_text = MIMEText(text_body, "plain", "utf-8")
    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls()

        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        # Envelope sender is SMTP_USERNAME to ensure Google SMTP delivery alignment
        server.sendmail(SMTP_USERNAME, [recipient_email], msg.as_string())
        server.quit()

        logger.info(f"Email successfully delivered to {recipient_email}")
        return {"success": True, "recipient": recipient_email}

    except smtplib.SMTPAuthenticationError as e:
        err_msg = "SMTP Authentication failed. Please verify App Password in .env"
        logger.error(f"{err_msg}: {e}")
        return {"success": False, "error": err_msg}
    except Exception as e:
        err_msg = f"Failed to send email to {recipient_email}: {str(e)}"
        logger.error(err_msg)
        return {"success": False, "error": str(e)}
