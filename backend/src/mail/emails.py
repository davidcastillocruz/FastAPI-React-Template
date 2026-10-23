from src.core.languages import get_response
from src.mail.layout import render_email

# Each email: its texts (mail/translations), what fills their gaps and what it shows under the text. The HTML is the
# same for all of them (layout.py). Each returns (subject, html): the subject goes as it is, it's a header and not HTML


# Test email of the demo: the address went through the whole stack, and the board says it was delivered
def build_demo_email(language: str) -> tuple[str, str]:
    texts = get_response("DEMO_EMAIL", language)
    return texts["subject"], render_email(language, texts, board=texts["status"])
