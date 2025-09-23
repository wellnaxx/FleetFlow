from datetime import datetime, timezone

ISO_FMT = "%Y-%m-%dT%H:%M:%S"

def dt_to_str(dt: datetime | None) -> str | None:
    if dt is None: return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)  # store naive UTC
    return dt.strftime(ISO_FMT)

def dt_from_str(s: str | None) -> datetime | None:
    if not s: return None
    return datetime.strptime(s, ISO_FMT)