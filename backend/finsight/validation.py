import re


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def normalize_email(value):
    return value.strip().lower() if isinstance(value, str) else ""


def validate_registration(data):
    errors = {}
    name = data.get("name", "")
    email = normalize_email(data.get("email"))
    password = data.get("password", "")
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100:
        errors["name"] = "Enter your name (2 to 100 characters)."
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        errors["email"] = "Enter a valid email address."
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        errors["password"] = "Use a password between 8 and 128 characters."
    return errors


def validate_password(password):
    return isinstance(password, str) and 8 <= len(password) <= 128
