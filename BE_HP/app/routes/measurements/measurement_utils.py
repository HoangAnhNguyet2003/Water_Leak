from werkzeug.exceptions import NotFound, BadRequest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ...utils import find_by_id, oid as _oid
from ...extensions import get_db

COL = "meter_measurements"

def get_latest_flow(mid: str) -> dict:
    if not find_by_id(mid, 'meters'):
        raise NotFound("Meter not found")
    
    db = get_db()
    doc = db[COL].find_one(
        {"meter_id": _oid(mid)},
        sort=[("measurement_time", -1)]
    )
    if not doc:
        raise NotFound("No measurements for this meter")
    
    return {
        "instant_flow": float(doc.get("instant_flow", 0)),
        "instant_pressure": float(doc.get("instant_pressure", 0)),
        "measurement_time": doc["measurement_time"].isoformat()
    }

def get_daily_flow(mid: str, date_str: str) -> dict:
    if not find_by_id(mid, 'meters'):
        raise NotFound("Meter not found")
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise BadRequest("Invalid date format, expected YYYY-MM-DD")
    
    db = get_db()
    start = day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end   = start + timedelta(days=1)

    cur = db[COL].find(
        {"meter_id": _oid(mid), "measurement_time": {"$gte": start, "$lt": end}},
        sort=[("measurement_time", 1)]
    )

    items = []
    for d in cur:
        items.append({
            "time": d["measurement_time"].isoformat(),
            "instant_flow": float(d.get("instant_flow", 0)),
            "instant_pressure": float(d.get("instant_pressure", 0)),
        })


    return {"items": items}