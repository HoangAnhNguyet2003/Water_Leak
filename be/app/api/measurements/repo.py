from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from ...extensions import get_db

COL = "meter_measurements"  # đổi nếu bạn đặt tên khác

def _oid(v): return v if isinstance(v, ObjectId) else ObjectId(v)

def find_latest_instant_flow(meter_id: str) -> Optional[Dict[str, Any]]:
    """
    Lấy bản ghi đo mới nhất cho 1 meter: {instant_flow, instant_pressure, measurement_time}
    """
    db = get_db()
    doc = db[COL].find_one(
        {"meter_id": _oid(meter_id)},
        sort=[("measurement_time", -1)]
    )
    if not doc:
        return None
    return {
        "instant_flow": float(doc.get("instant_flow", 0)),
        "instant_pressure": float(doc.get("instant_pressure", 0)),
        "measurement_time": doc["measurement_time"].isoformat()
    }

def list_instant_flow_daily(meter_id: str, day_utc: datetime) -> List[Dict[str, Any]]:
    """
    Tất cả bản ghi trong 1 ngày (UTC) cho meter: [{time, instant_flow, instant_pressure}]
    """
    db = get_db()
    start = day_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end   = start + timedelta(days=1)

    cur = db[COL].find(
        {"meter_id": _oid(meter_id), "measurement_time": {"$gte": start, "$lt": end}},
        sort=[("measurement_time", 1)]
    )
    out = []
    for d in cur:
        out.append({
            "time": d["measurement_time"].isoformat(),
            "instant_flow": float(d.get("instant_flow", 0)),
            "instant_pressure": float(d.get("instant_pressure", 0)),
        })
    return out