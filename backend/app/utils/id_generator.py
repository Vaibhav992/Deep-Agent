import uuid
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """Generate a short, sortable unique ID with optional prefix."""
    ts = int(datetime.utcnow().timestamp() * 1000)
    short_uuid = uuid.uuid4().hex[:8]
    if prefix:
        return f"{prefix}_{ts}_{short_uuid}"
    return f"{ts}_{short_uuid}"


def generate_uuid() -> str:
    return str(uuid.uuid4())
