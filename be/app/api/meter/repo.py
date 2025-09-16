from typing import Optional, Dict, Any, List, Tuple

from bson import ObjectId
from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str
from datetime import datetime
from werkzeug.exceptions import NotFound, Conflict
from ...extensions import get_db
from pymongo import errors
import hashlib
COL = "meters"

# def insert(doc: Dict[str, Any]) -> Dict[str, Any]:
#     res = get_db()[COL].insert_one(doc)
#     return get(oid_str(res.inserted_id))

COL = "meters"

def _db_to_api(d: dict) -> dict:
    print(f"{d.keys()}")
    if "_id" in d:
        print("Converting _id to id for document:", d)
        d["id"] = oid_str(d.pop("_id"))
    for key in d:
        if isinstance(d[key], ObjectId):
            d[key] = oid_str(d[key])
    return d

def _meter_id_from_name(meter_name: str) -> str:
    # md5 đơn giản, ổn định, không phụ thuộc DB
    return hashlib.md5(meter_name.strip().encode("utf-8")).hexdigest()

def find_branch_by_name(branch_name: str) -> Dict[str, Any]:
    db = get_db()
    b = db.branches.find_one({"name": branch_name})
    print(f"Finding branch by name '{branch_name}':", b)
    if not b:
        raise NotFound(f"Branch '{branch_name}' not found")
    return b

def exists_meter_by_branchid_meterid(branch_id: ObjectId, meter_id: str) -> bool:
    db = get_db()
    return db[COL].find_one({"branch_id": branch_id, "meter_id": meter_id}) is not None

def insert_meter(branch_id: ObjectId, meter_name: str, installation_time: Optional[datetime]) -> Dict[str, Any]:
    db = get_db()
    meter_id = _meter_id_from_name(meter_name)

    if exists_meter_by_branchid_meterid(branch_id, meter_id):
        raise Conflict("Meter already exists in this branch")

    doc = {
        "branch_id": branch_id,
        "meter_id": meter_id,
        "meter_name": meter_name.strip(),
        "installation_time": installation_time or datetime.utcnow(),
    }
    try:
        res = db[COL].insert_one(doc)
    except errors.DuplicateKeyError as e:
        # Nếu 2 request song song, unique index sẽ chặn ở đây
        raise ("Meter already exists in this branch") from e

    return {
        "id": str(res.inserted_id),
        "branch_id": str(branch_id),
        "meter_id": meter_id,
        "meter_name": doc["meter_name"],
        "installation_time": doc["installation_time"].isoformat(),
    }

def insert(doc: dict) -> dict:
    payload = {
        "branch_id": to_object_id(doc["branch_id"]),
        "meter_name": doc["meter_name"],
        "installation_time": doc.get("installation_time"),
    }
    res = get_db()[COL].insert_one(payload)
    payload["_id"] = res.inserted_id
    print("Insert payload:", payload)
    print("Inserted ID:", res.inserted_id)
    return _db_to_api(payload)


def get(mid: str) -> Optional[Dict[str, Any]]:
    d = get_db()[COL].find_one({"_id": to_object_id(mid)})
    print("Get meter by ID:", mid, "Result:", d)
    if not d: return None
    d["id"] = oid_str(d.pop("_id"))
    print("Found meter document:", d)
    d["branch_id"] = oid_str(d["branch_id"])
    print("Converted meter document:", d)
    return d

def list_paginated(page:int, page_size:int, branch_ids: Optional[list[str]], q: Optional[str], sort: Optional[str]) -> Tuple[List[Dict[str,Any]], bool]:
    db = get_db()
    flt: Dict[str, Any] = {}
    if branch_ids:
        flt["branch_id"] = {"$in": [to_object_id(x) for x in branch_ids]}
    if q:
        flt["meter_name"] = {"$regex": q, "$options": "i"}

    srt = [("_id",1)]
    if sort:
        field = sort.lstrip("-"); direc = -1 if sort.startswith("-") else 1
        srt = [(field, direc)]

    skip = (page-1) * page_size
    cur = db[COL].find(flt).sort(srt).skip(skip).limit(page_size+1)

    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        d["branch_id"] = oid_str(d["branch_id"])
        out.append(d)
    has_next = len(out) > page_size
    if has_next: out = out[:page_size]
    return out, has_next

def update(mid: str, patch: Dict[str, Any]) -> bool:
    res = get_db()[COL].update_one({"_id": to_object_id(mid)}, {"$set": patch})
    return res.matched_count == 1

def delete(mid: str) -> bool:
    db = get_db()
    meter_oid = to_object_id(mid)
    try:
        res = db[COL].delete_one({"_id": meter_oid})
        if res.deleted_count == 1:
            db["user_meter"].delete_many({"meter_id": meter_oid})
            return True
        return False
    except Exception:
        return False
