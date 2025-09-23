from datetime import datetime, timezone
from werkzeug.exceptions import NotFound, BadRequest
from ..meter.repo import get as get_meter  # 
from .repo import find_latest_instant_flow, list_instant_flow_daily

def get_latest_flow(mid: str) -> dict:
    if not get_meter(mid):
        raise NotFound("Meter not found")
    doc = find_latest_instant_flow(mid)
    if not doc:
        raise NotFound("No measurements for this meter")
    return doc

def get_daily_flow(mid: str, date_str: str) -> dict:
    if not get_meter(mid):
        raise NotFound("Meter not found")
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise BadRequest("Invalid date format, expected YYYY-MM-DD")
    items = list_instant_flow_daily(mid, day)
    return {"items": items}