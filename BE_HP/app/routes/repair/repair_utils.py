from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from werkzeug.exceptions import Conflict, Forbidden, BadRequest
from ...utils import (
    json_ok,
    created,
    parse_pagination,
    role_name as _role_name,
    oid_str,
    get_user_scope,
    to_object_id,
)
from ...extensions import get_db

COL = "meter_repairs"

def get(rid: str) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết 1 repair"""
    d = get_db()[COL].find_one({"_id": to_object_id(rid)})
    if not d:
        return None
    d["id"] = oid_str(d.pop("_id"))
    if d.get("meter_id"):
        d["meter_id"] = oid_str(d["meter_id"])
    return d


def list_repair_paginated(
    page: int, page_size: int, q: Optional[str], sort: Optional[str]
) -> Tuple[List[Dict[str, Any]], bool]:
    """Lấy danh sách repairs phân trang"""
    db = get_db()
    flt: Dict[str, Any] = {}

    if q:
        flt["$or"] = [
            {"leak_reason": {"$regex": q, "$options": "i"}},
            {"leak_fix": {"$regex": q, "$options": "i"}},
            {"replacement_location": {"$regex": q, "$options": "i"}},
            {"replacement_type": {"$regex": q, "$options": "i"}},
        ]

    srt = [("_id", 1)]
    if sort:
        field = sort.lstrip("-")
        direc = -1 if sort.startswith("-") else 1
        srt = [(field, direc)]

    skip = (page - 1) * page_size
    cur = db[COL].find(flt).sort(srt).skip(skip).limit(page_size + 1)

    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        if d.get("meter_id"):
            d["meter_id"] = oid_str(d["meter_id"])
        out.append(d)

    has_next = len(out) > page_size
    if has_next:
        out = out[:page_size]
    return out, has_next


from bson import ObjectId

def list_repair_paginated(
    page: int,
    page_size: int,
    q: Optional[str],
    sort: Optional[str],
    base_filter: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    db = get_db()
    flt: Dict[str, Any] = base_filter.copy() if base_filter else {}

    if q:
        flt["$or"] = [
            {"leak_reason": {"$regex": q, "$options": "i"}},
            {"leak_fix": {"$regex": q, "$options": "i"}},
            {"replacement_location": {"$regex": q, "$options": "i"}},
            {"replacement_type": {"$regex": q, "$options": "i"}},
        ]

    srt = [("_id", 1)]
    if sort:
        field = sort.lstrip("-")
        direc = -1 if sort.startswith("-") else 1
        srt = [(field, direc)]

    skip = (page - 1) * page_size
    cur = db[COL].find(flt).sort(srt).skip(skip).limit(page_size + 1)

    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        meter_id = None
        meter_name = None

        if d.get("meter_id"):
            meter_id = oid_str(d["meter_id"])
            meter = db["meters"].find_one({"_id": ObjectId(meter_id)})
            meter_name = meter.get("meter_name") if meter else None

        d["meter_id"] = meter_id
        d["meter_name"] = meter_name
        out.append(d)

    has_next = len(out) > page_size
    if has_next:
        out = out[:page_size]

    return out, has_next
