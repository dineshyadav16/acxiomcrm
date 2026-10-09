"""Small validation functions used by forms and the REST API."""

import re


def valid_email(email):
    """Return True when the email has a basic valid format."""
    if not email:
        return False

    pattern = r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+$"
    return re.match(pattern, email) is not None


def valid_phone(phone):
    """Allow digits, spaces, brackets, hyphens and an optional + sign."""
    if not phone:
        return False

    pattern = r"^\+?[0-9\s\-()]{7,20}$"
    return re.match(pattern, phone) is not None


def valid_pwd(password):
    """Return (is_valid, error_message) for a new password."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters."

    has_uppercase = re.search(r"[A-Z]", password)
    has_lowercase = re.search(r"[a-z]", password)
    has_number = re.search(r"[0-9]", password)
    has_symbol = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)

    if not (has_uppercase and has_lowercase and has_number and has_symbol):
        message = "Use uppercase, lowercase, a number and a special symbol."
        return False, message

    return True, None
