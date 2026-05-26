import secrets
import string


def generate_gift_code() -> str:
    """
    Generate a cryptographically secure gift card code.
    Format: XXXX-XXXX-XXXX-XXXX (16 alphanumeric chars, uppercase)
    """
    chars = string.ascii_uppercase + string.digits
    groups = []
    for _ in range(4):
        group = ''.join(secrets.choice(chars) for _ in range(4))
        groups.append(group)
    return '-'.join(groups)


def validate_card_code(code: str) -> bool:
    """Validate a gift card code format."""
    import re
    pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
    return bool(re.match(pattern, code))