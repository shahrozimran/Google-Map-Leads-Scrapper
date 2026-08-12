# Implementation Plan: Free Automated Cold Email Outreach (Stremly Branded)

Add an automated email outreach module to contact scraped business leads with personalized, professional cold email pitches for **Stremly** (`stremly.site`) — Creative Software & AI Studio.

---

## 📌 Dynamic Column Variable Mapping

Every outreach email dynamically extracts its variables from the corresponding row columns in Google Sheets:

| Email Variable | Target Column in Google Sheet | Example Extraction | Fallback if Blank |
|---|---|---|---|
| **`{business_name}`** | **`Name`** Column | `"EURO JAPAN"` | `"your team"` |
| **`{location}`** | **`Address`** Column | `"Minato City, Tokyo"` | `"your area"` |
| **`{category}`** | **`Category`** Column | `"Car Dealer"` | `"your industry"` |

---

## 🛡️ Primary Inbox Deliverability & Anti-Spam Optimizations

To guarantee emails land in the **Primary Inbox** rather than Spam or Promotions:

1. **No Emojis:** Strictly zero emojis in subject lines or email bodies (emojis trigger automated spam algorithms).
2. **Multi-Part MIME (Plain-Text + HTML):** Every message includes both clean HTML **and** a plain-text alternative (`multipart/alternative`), a key requirement for inbox delivery algorithms.
3. **No Spam-Trigger Keywords:** Zero buzzwords such as "Free", "Guarantee", "Limited Time", "Act Now", or "Click Here".
4. **Dynamic Personalization:** Every email dynamically pulls `{business_name}` from the `Name` column and `{location}` from the `Address` column.
5. **Authentic Sender Headers:** Sent via official Gmail SMTP with valid Message-ID, DKIM/SPF alignment, and an unsubscribe footer.

---

## 🎨 Stremly Professional HTML & CSS Email Template

Clean, modern inline CSS (dark border accents, crisp typography, responsive layout):

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 20px; background-color: #f4f5f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #e1e4e8; border-radius: 6px; overflow: hidden;">
    <!-- Header with Stremly Logo -->
    <tr>
      <td style="padding: 24px 32px; background: #09090b; border-bottom: 3px solid #10b981;">
        <img src="cid:stremly_logo" alt="Stremly" style="height: 36px; width: auto; display: block;" />
      </td>
    </tr>
    <!-- Content Body -->
    <tr>
      <td style="padding: 32px; color: #1f2937; font-size: 15px; line-height: 1.6;">
        <p style="margin-top: 0; font-weight: 600; color: #111827; font-size: 16px;">
          Hi {business_name} Team,
        </p>
        <p style="margin-bottom: 20px;">
          I noticed your business in {location} and wanted to reach out directly. At Stremly, we build custom software and intelligent automation solutions designed to help established businesses scale efficiently.
        </p>
        <p style="margin-bottom: 12px; font-weight: 600; color: #111827;">
          How we help our partners:
        </p>
        <ul style="margin: 0 0 24px 0; padding-left: 20px; color: #374151;">
          <li style="margin-bottom: 8px;"><strong>Process &amp; AI Automation:</strong> Streamline customer follow-ups, workflows, and manual data tasks.</li>
          <li style="margin-bottom: 8px;"><strong>Web &amp; Software Development:</strong> Build high-performing web applications and custom business portals.</li>
          <li style="margin-bottom: 8px;"><strong>System Enhancements:</strong> Upgrade existing platforms for speed, security, and mobile experience.</li>
        </ul>
        <p style="margin-bottom: 28px;">
          Would you be open to a brief 5-minute conversation this week to see if any of our solutions align with your current goals?
        </p>
        <!-- Button CTA -->
        <table role="presentation" cellspacing="0" cellpadding="0">
          <tr>
            <td style="border-radius: 4px; background: #09090b;">
              <a href="https://stremly.site" target="_blank" style="padding: 12px 24px; color: #ffffff; text-decoration: none; font-weight: 600; display: inline-block; font-size: 14px;">View Our Work at stremly.site &rarr;</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    <!-- Footer -->
    <tr>
      <td style="padding: 20px 32px; background: #f9fafb; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; line-height: 1.5;">
        <strong>Stremly Studio</strong> &bull; Creative Software &amp; AI Studio<br>
        Website: <a href="https://stremly.site" style="color: #10b981; text-decoration: none;">https://stremly.site</a><br><br>
        <span style="color: #9ca3af;">If you prefer not to receive future updates, please reply with "unsubscribe".</span>
      </td>
    </tr>
  </table>
</body>
</html>
```

---

## 💡 3-State Email Tracking System

| State | Condition | Campaign Action |
|---|---|---|
| **`Not Sent`** | Valid email exists, campaign has not run yet. | **Send Email** |
| **`Sent`** | Email delivered successfully. | **Skip** |
| **`NULL`** | No email found for this lead. | **Skip** |

---

## Proposed Changes

### Backend Components

#### [NEW] [email_templates.py](file:///d:/Desktop/Projects/Google%20Map%20Leads%20Generater/email_templates.py)
- Responsive HTML + plain-text email generators.
- Zero emojis, clean typography.
- Extracts `{business_name}` from **`Name`** column and `{location}` from **`Address`** column.
- Embedded logo CID generator for `Stremly Green Back.jpg.jpeg`.

#### [NEW] [email_sender.py](file:///d:/Desktop/Projects/Google%20Map%20Leads%20Generater/email_sender.py)
- `smtplib` sender supporting Gmail TLS (`smtp.gmail.com:587`).
- `multipart/alternative` formatting for primary inbox delivery.
- Randomized delay (5–15s per email) anti-spam throttling.

#### [MODIFY] [sheets/google_sheets.py](file:///d:/Desktop/Projects/Google%20Map%20Leads%20Generater/sheets/google_sheets.py)
- `Email Status` column handling (Sent, Not Sent, NULL).
- Live row status updater helper (`update_row_email_status`).

#### [MODIFY] [app.py](file:///d:/Desktop/Projects/Google%20Map%20Leads%20Generater/app.py)
- Route `POST /api/send-outreach` to process campaign queue with SSE trace logging.

---

### Frontend Components

#### [NEW] [EmailOutreachModal.jsx](file:///d:/Desktop/Projects/Google%20Map%20Leads%20Generater/frontend/src/components/EmailOutreachModal.jsx)
- Stremly campaign launch modal with HTML email preview, sender settings, and real-time color-coded trace log console.

#### [MODIFY] [App.jsx](file:///d:/Desktop/Projects/Google%20Map%20Leads%20Generater/frontend/src/App.jsx)
- **"Send Emails"** action button in dashboard header.

---

## Verification Plan

### Automated & Deliverability Tests
1. **Column Mapping Verification:** Confirm `{business_name}` reads from `Name` and `{location}` reads from `Address`.
2. **Fallback Verification:** Confirm blank addresses safely default to `"your area"`.
3. **No-Emoji & Multi-Part MIME Test:** Verify message structure contains `multipart/alternative` without emojis.
4. **Live Status Flip Test:** Verify row status in Google Sheets changes from `Not Sent` $\rightarrow$ `Sent` immediately.
