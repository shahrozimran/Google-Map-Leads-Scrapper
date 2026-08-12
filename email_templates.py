"""
Stremly Studio High-Converting Cold Email Template Generator.
Combines premium modern typography, crisp aesthetic styling, and persuasive pitching copy.
"""

def sanitize_variable(val, fallback):
    """Sanitize input variable and return fallback if blank or None."""
    if not val or not str(val).strip() or str(val).strip().lower() in ['none', 'null', 'nan', 'n/a']:
        return fallback
    return str(val).strip()

def generate_email_content(business_name=None, location=None, category=None):
    """
    Generates subject, HTML body, and plain-text body for a lead.
    
    Dynamic Variable Mapping:
    - business_name: Extracted from 'Name' column (fallback: 'your team')
    - location: Extracted from 'Address' column (fallback: 'your area')
    - category: Extracted from 'Category' column (fallback: 'your industry')
    """
    clean_name = sanitize_variable(business_name, "your team")
    clean_location = sanitize_variable(location, "your area")
    clean_category = sanitize_variable(category, "your industry")

    subject = f"Growth & Automation Opportunities for {clean_name}"

    text_body = f"""Hi {clean_name} Team,

I noticed your business in {clean_location} and wanted to reach out directly. 

At Stremly Studio, we build custom web applications, business portals, and intelligent AI automation solutions designed to help established businesses scale efficiency and streamline daily operations.

How we help teams like yours:
• AI & Workflow Automation: Automate customer follow-ups, CRM sync, and manual data tasks.
• Web & Software Development: Build high-speed custom web platforms, portals, and web apps.
• System Optimization: Upgrade existing digital platforms for speed, security, and higher conversion rates.

Would you be open to a brief 5-minute conversation this week to see if any of our solutions align with your current tech goals?

Explore Our Work: https://stremly.site

Best regards,

Stremly Team
Creative Software & AI Studio
Website: https://stremly.site

If you prefer not to receive future emails, reply with "unsubscribe".
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 24px 12px; background-color: #f4f5f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
    
    <!-- Top Emerald Accent Bar & Header -->
    <tr>
      <td style="padding: 24px 32px; background: #09090b; border-bottom: 3px solid #10b981;">
        <table width="100%" cellspacing="0" cellpadding="0">
          <tr>
            <td>
              <span style="color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; font-family: sans-serif;">STREMLY</span>
              <span style="color: #10b981; font-size: 26px; font-weight: 800;">.</span>
              <span style="color: #a1a1aa; font-size: 12px; margin-left: 6px; font-weight: 600; letter-spacing: 1px; display: inline-block;">STUDIO</span>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Content Body -->
    <tr>
      <td style="padding: 36px 32px; color: #1e293b; font-size: 15px; line-height: 1.65;">
        <p style="margin-top: 0; font-weight: 700; color: #0f172a; font-size: 17px; margin-bottom: 16px;">
          Hi {clean_name} Team,
        </p>
        
        <p style="margin-bottom: 24px; color: #334155;">
          I noticed your business in <strong>{clean_location}</strong> and wanted to reach out directly. At <strong>Stremly Studio</strong>, we build custom software, web platforms, and intelligent AI automation tools designed to help established businesses scale efficiently.
        </p>

        <div style="background-color: #f8fafc; border-left: 4px solid #10b981; padding: 18px 20px; border-radius: 6px; margin-bottom: 28px;">
          <p style="margin: 0 0 10px 0; font-weight: 700; color: #0f172a; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">
            How We Help Our Partners:
          </p>
          <ul style="margin: 0; padding-left: 18px; color: #334155; font-size: 14px;">
            <li style="margin-bottom: 8px;"><strong>Process &amp; AI Automation:</strong> Streamline customer follow-ups, CRM updates, and manual tasks.</li>
            <li style="margin-bottom: 8px;"><strong>Web &amp; Custom Software:</strong> Build high-performing web apps, customer portals, and internal tools.</li>
            <li style="margin-bottom: 0;"><strong>System Optimization:</strong> Upgrade existing digital platforms for maximum speed, security, and sales conversions.</li>
          </ul>
        </div>

        <p style="margin-bottom: 28px; color: #334155;">
          Would you be open to a brief 5-minute conversation this week to see if any of our solutions align with your current goals?
        </p>

        <!-- CTA Button -->
        <table role="presentation" cellspacing="0" cellpadding="0" style="margin-bottom: 12px;">
          <tr>
            <td style="border-radius: 8px; background: #09090b; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);">
              <a href="https://stremly.site" target="_blank" style="padding: 14px 28px; color: #ffffff; text-decoration: none; font-weight: 700; display: inline-block; font-size: 14px; border: 1px solid #10b981; border-radius: 8px;">View Our Work at stremly.site &rarr;</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Sign-off & Footer -->
    <tr>
      <td style="padding: 24px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 13px; line-height: 1.5;">
        <p style="margin: 0 0 4px 0; font-weight: 700; color: #0f172a; font-size: 14px;">Stremly Team</p>
        <p style="margin: 0 0 12px 0; color: #64748b;">Creative Software &amp; AI Studio &bull; <strong>Stremly Studio</strong></p>
        <p style="margin: 0 0 12px 0;">Website: <a href="https://stremly.site" style="color: #10b981; text-decoration: none; font-weight: 600;">https://stremly.site</a></p>
        <div style="font-size: 11px; color: #94a3b8; border-top: 1px solid #cbd5e1; padding-top: 12px; margin-top: 12px;">
          If you prefer not to receive future updates, reply with "unsubscribe".
        </div>
      </td>
    </tr>

  </table>
</body>
</html>
"""

    return {
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body
    }
