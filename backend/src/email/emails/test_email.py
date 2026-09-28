"""
Confirmation email template used to verify SMTP configuration.

Exposes a single `render()` function that returns the three parts of
an email: subject, HTML body, and plain-text body. The subject and
plain-text body are simple strings; the HTML is a self-contained
document with inline styles only, designed to render reliably across
common email clients (Gmail, Apple Mail, Outlook).

No template engine is used. The values are static, so building them
at call time with plain strings is simpler and has no runtime cost.
"""


def render() -> tuple[str, str, str]:
    """Build the test email content.

    Returns the three parts as a tuple, in the order expected by
    `src.email.sender.send_email`:

        subject, html_body, text_body = test_email.render()

    All three are plain strings. The HTML body uses only inline styles
    and table-based layout, which is the safest approach for email
    clients that strip `<style>` blocks or do not support modern CSS
    (flexbox, grid, custom properties).

    Returns:
        A tuple of `(subject, html_body, text_body)`.
    """
    subject = "Test email from FastAPI Template"

    html_body = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  </head>
  <body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="padding:48px 16px;">
      <tr>
        <td align="center">
          <table width="560" cellpadding="0" cellspacing="0" role="presentation"
                 style="max-width:560px;width:100%;background:#1e293b;border-radius:16px;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,0.35);">

            <!-- Top gradient bar -->
            <tr>
              <td style="height:6px;background:linear-gradient(90deg,#6366f1 0%,#8b5cf6 50%,#ec4899 100%);"></td>
            </tr>

            <!-- Icon + Title -->
            <tr>
              <td align="center" style="padding:40px 32px 8px;">
                <div style="width:72px;height:72px;border-radius:50%;background:rgba(99,102,241,0.15);display:inline-block;line-height:72px;">
                  <span style="font-size:36px;">✅</span>
                </div>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:8px 32px 0;">
                <h1 style="margin:0;font-size:24px;font-weight:700;color:#f1f5f9;letter-spacing:-0.02em;">
                  Everything is working
                </h1>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:12px 40px 0;">
                <p style="margin:0;font-size:15px;line-height:1.6;color:#94a3b8;">
                  If you're reading this, your SMTP configuration is correct and
                  emails are being delivered successfully.
                </p>
              </td>
            </tr>

            <!-- Divider -->
            <tr>
              <td style="padding:28px 40px 0;">
                <div style="height:1px;background:linear-gradient(90deg,transparent,#334155 50%,transparent);"></div>
              </td>
            </tr>

            <!-- Status chips -->
            <tr>
              <td align="center" style="padding:24px 40px 36px;">
                <table cellpadding="0" cellspacing="0" role="presentation">
                  <tr>
                    <td style="padding:0 6px;">
                      <span style="display:inline-block;padding:6px 14px;border-radius:999px;background:rgba(16,185,129,0.15);color:#34d399;font-size:12px;font-weight:600;letter-spacing:0.02em;">
                        ● SMTP OK
                      </span>
                    </td>
                    <td style="padding:0 6px;">
                      <span style="display:inline-block;padding:6px 14px;border-radius:999px;background:rgba(99,102,241,0.15);color:#a5b4fc;font-size:12px;font-weight:600;letter-spacing:0.02em;">
                        ● Async Delivery
                      </span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td align="center" style="padding:20px;background:#0f172a;border-top:1px solid #1e293b;">
                <p style="margin:0;font-size:12px;color:#64748b;">
                  © 2025 FastAPI Template
                </p>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    text_body = (
        "Everything is working.\n\n"
        "If you're reading this, your SMTP configuration is correct "
        "and emails are being delivered successfully.\n"
    )

    return subject, html_body, text_body