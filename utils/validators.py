import re
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(email and EMAIL_RE.match(email))


def parse_date(value):
    if not value:
        return None, None
    try:
        return datetime.strptime(value, "%Y-%m-%d"), None
    except ValueError:
        return None, "Invalid date format. Use YYYY-MM-DD."


def to_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
