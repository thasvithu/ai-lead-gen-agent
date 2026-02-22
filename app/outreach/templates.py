"""
app/outreach/templates.py — Email template rendering.

Wraps the AI-drafted plain-text email in a clean HTML structure
for better deliverability and readability. Also provides a plain-
text fallback since many clients prefer it.
"""

from dataclasses import dataclass


@dataclass
class RenderedEmail:
    """Final email ready to be sent — subject, HTML body, plain-text body."""
    subject: str
    html_body: str
    plain_body: str


def render_email(subject: str, plain_body: str, sender_name: str = "Vithusan") -> RenderedEmail:
    """
    Wrap an AI-drafted plain-text email in a clean HTML template.

    Args:
        subject:     Email subject line (from AI draft).
        plain_body:  Plain-text email body (from AI draft).
        sender_name: Name to sign off with (from config or default).

    Returns:
        RenderedEmail with subject, HTML body, and plain-text body.
    """
    # Convert plain text newlines to HTML paragraphs
    paragraphs = [
        f"<p>{line}</p>" if line.strip() else "<br>"
        for line in plain_body.strip().splitlines()
    ]
    html_content = "\n".join(paragraphs)

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 15px;
      line-height: 1.6;
      color: #1a1a1a;
      background: #ffffff;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 40px auto;
      padding: 0 24px;
    }}
    p {{
      margin: 0 0 12px 0;
    }}
    .signature {{
      margin-top: 32px;
      color: #555;
      font-size: 14px;
      border-top: 1px solid #eee;
      padding-top: 16px;
    }}
  </style>
</head>
<body>
  <div class="container">
    {html_content}
    <div class="signature">
      <strong>{sender_name}</strong>
    </div>
  </div>
</body>
</html>"""

    return RenderedEmail(
        subject=subject,
        html_body=html_body,
        plain_body=plain_body,
    )
