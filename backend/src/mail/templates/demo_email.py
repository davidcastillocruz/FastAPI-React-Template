from html import escape

from src.core.languages import get_response

# Colors of the light theme of the frontend (frontend/src/themes/themes.css):
# station signage, black ink on warm paper with signal yellow, and the dark departures board
PAPER = "#efece4"
INK = "#151513"
MUTED = "#5c5a53"
BORDER = "#c9c4b6"
SIGNAL = "#f5c400"
BOARD = "#1a1a18"
BOARD_CELL = "#262624"
BOARD_TEXT = "#f4f1e8"

# Email clients rarely load web fonts: Archivo if it's installed, a narrow system font otherwise
FONT = "Archivo, 'Arial Narrow', Arial, Helvetica, sans-serif"

# The stops of the email, the same line as the home page
STATIONS = ("React", "FastAPI", "PostgreSQL", "Mailpit")

# Email clients only render tables and inline styles reliably: every piece below is built with them


# A word of the departures board, one flap per character
def _flaps(text: str) -> str:
    cells = "".join(
        f'<td style="width:26px;height:36px;padding:0;background:{BOARD_CELL};border-radius:3px;'
        f'color:{BOARD_TEXT};font:700 20px/36px {FONT};text-align:center;">'
        f'{escape(char) if char != " " else "&nbsp;"}</td>'
        for char in text.upper()
    )
    return f'<table role="presentation" cellpadding="0" cellspacing="3"><tr>{cells}</tr></table>'


# The line of the home page with every station lit: the email got to the last one
def _route() -> str:
    def track(visible: bool) -> str:
        color = INK if visible else "transparent"
        return f'<td style="padding:0;"><div style="height:2px;background:{color};"></div></td>'

    stations = "".join(
        f'<td width="25%" valign="top" style="padding:0;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f"{track(index > 0)}"
        f'<td width="16" style="padding:0;"><div style="width:12px;height:12px;border:2px solid {INK};'
        f'border-radius:50%;background:{SIGNAL};"></div></td>'
        f"{track(index < len(STATIONS) - 1)}"
        f"</tr></table>"
        f'<div style="padding-top:8px;text-align:center;font:700 13px/1.3 {FONT};color:{INK};">{name}</div>'
        f"</td>"
        for index, name in enumerate(STATIONS)
    )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{stations}</tr></table>'


# Test email of the demo: subject and HTML body in the user's language, styled like the home page
def build_demo_email(language: str) -> tuple[str, str]:
    raw = get_response("DEMO_EMAIL", language)
    # Escaped for the HTML. The subject goes as it is (it's a header, not HTML)
    # and the status raw: _flaps escapes each flap
    texts = {key: escape(text) for key, text in raw.items()}
    body = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{texts["subject"]}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
<tr><td style="padding-bottom:18px;border-bottom:1px solid {BORDER};font:700 15px/1 {FONT};color:{INK};">
FastAPI <span style="font-weight:400;color:{MUTED};">&amp;</span> React
</td></tr>
<tr><td style="padding:36px 0 12px;font:800 44px/1 {FONT};letter-spacing:-1px;color:{INK};">{texts["title"]}</td></tr>
<tr><td style="padding-bottom:28px;font:400 16px/1.55 {FONT};color:{MUTED};">{texts["text"]}</td></tr>
<tr><td style="padding:20px;background:{BOARD};border-radius:12px;">
<div style="padding:0 0 10px 3px;font:700 11px/1 {FONT};letter-spacing:1.5px;text-transform:uppercase;color:{SIGNAL};">
{texts["board"]}
</div>
{_flaps(raw["status"])}
</td></tr>
<tr><td style="padding:32px 0;">{_route()}</td></tr>
<tr><td style="padding-top:18px;border-top:1px solid {BORDER};font:400 13px/1.5 {FONT};color:{MUTED};">
{texts["footer"]}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
    return raw["subject"], body
