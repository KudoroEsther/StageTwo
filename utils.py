from datetime import datetime, timezone
from uuid6 import uuid7

def generate_uuid():
    return str(uuid7())

def utc_now():
    return datetime.now(timezone.utc)

def classify_age(age: int):
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    return "senior"