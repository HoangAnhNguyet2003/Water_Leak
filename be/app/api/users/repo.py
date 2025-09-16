
from typing import Optional, Dict, Any, List, Tuple
import uuid
from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, errors, ReturnDocument
from werkzeug.exceptions import NotFound, Conflict

COL = "users"

# ==== QD edited ====
def get_role_name(role_oid: str) -> str:
    """Map role_id (oid string) sang roleName"""
    db = get_db()
    role = db["roles"].find_one({"_id": ObjectId(role_oid)})
    if not role:
        return "branch_manager"  # fallback
    return role.get("role_name", "branch_manager")

def get_branch_name_by_branch_id(branch_oid) -> str:
    """Map branch_id (oid string) sang branchName"""
    db = get_db()
    branch = db["branches"].find_one({"_id": branch_oid})
    if not branch:
        return None
    return branch.get("name", None)

def delete_user(uid: str) -> bool:
    db = get_db()
    try:
        obj_id = to_object_id(uid)
    except InvalidId:
        raise

    try:
        user = db["users"].find_one({"_id": obj_id})
        if not user:
            return False, "NOT_FOUND"

        if get_role_name(_oid_str(user.get("role_id"))) == "admin":
            return False, "FORBIDDEN"

        res = db["users"].delete_one({"_id": obj_id})
        if res.deleted_count != 1:
            return False, "NOT_FOUND"

        db["user_meter"].delete_many({"user_id": obj_id})

        return True, ""
    except Exception as e:
        return False, "ERROR"
# === End of QD edit ====


def _oid_str(v) -> str:
    return str(v) if isinstance(v, ObjectId) else v

def db_to_api(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return None
    out = {
        "id": str(doc["_id"]),
        "username": doc.get("username"),
        "role_name": doc.get("role_name"),
        "branch_id": str(doc["branch_id"]) if doc.get("branch_id") else None,
        "company_id": str(doc["company_id"]) if doc.get("company_id") else None,
        "is_active": bool(doc.get("is_active", True)),
    }
    return out

def find_role_by_name(role_name: str) -> Dict[str, Any]:
    db = get_db()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        raise NotFound(f"Role '{role_name}' not found")
    return role

def username_exists(username: str) -> bool:
    db = get_db()
    return db[COL].find_one({"username": username}) is not None

def username_taken_by_other(user_name: str, exclude_user_id: str = None) -> bool:
    db = get_db()
    query = {"username": user_name}
    if exclude_user_id:
        query["_id"] = {"$ne": ObjectId(exclude_user_id)}
    return db[COL].find_one(query) is not None

def insert_user(username: str, password_hash: str, role_id: ObjectId,
                role_name: str = None, is_active: bool = True, branch_id: ObjectId | None = None, last_login=None) -> Dict[str, Any]:
    db = get_db()

    doc = {
        "username": username,
        "password": password_hash,
        "role_id": role_id,
        "is_active": is_active,
        "branch_id": branch_id,
        "last_login": last_login,
    }
    res = db[COL].insert_one(doc)

    return {
        "id": _oid_str(res.inserted_id),
        "role_id": _oid_str(role_id),
        "username": username,
        "role_name": role_name,
        "is_active": is_active,
        "branch_id": _oid_str(branch_id) if branch_id else None,
        "last_login": last_login,
    }

def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()

    user = db[COL].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise NotFound("User not found")

    doc = db[COL].find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": updates, "$currentDate": {"updated_at": True}},
        return_document=ReturnDocument.AFTER
    )
    return db_to_api(doc)

def find_by_id(uid: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        doc = db[COL].find_one({"_id": to_object_id(uid)})
    except Exception:
        return None
    if not doc: return None
    doc["id"] = oid_str(doc.pop("_id"))
    return doc


def _build_filter(q: Optional[str]) -> Dict[str, Any]:
    if not q:
        return {}
    return {
        "$or": [
            {"name":  {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]
    }

def _build_sort(sort: Optional[str]):
    if not sort:
        return [("_id", 1)]
    field = sort.lstrip("-")
    direction = -1 if sort.startswith("-") else 1
    return [(field, direction)]

def list_users_paginated(page: int, page_size: int, q: Optional[str], sort: Optional[str], is_active: Optional[bool] = None) -> Tuple[List[Dict[str, Any]], bool]:
    db = get_db()
    flt = _build_filter(q)

    # Thêm filter theo is_active nếu được chỉ định
    if is_active is not None:
        flt["is_active"] = is_active

    srt = _build_sort(sort)
    skip = (page - 1) * page_size
    cur = db[COL].find(flt).sort(srt).skip(skip).limit(page_size + 1)
    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        out.append(d)
    has_next = len(out) > page_size
    if has_next:
        out = out[:page_size]
    return out, has_next

def list_users_all() -> List[Dict[str, Any]]:
    """Lấy tất cả users không phân trang"""
    db = get_db()
    flt = {}

    cur = db[COL].find(flt).sort([("_id", 1)])
    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        out.append(d)
    return out

def update_user_meter_relationships(user_id: str, meter_ids: list[str]):
    db = get_db()
    user_oid = ObjectId(user_id)

    db["user_meter"].delete_many({"user_id": user_oid})

    if meter_ids:
        meter_oids = [ObjectId(mid) for mid in meter_ids]
        existing_meters = db["meters"].find({"_id": {"$in": meter_oids}})
        existing_meter_ids = {str(m["_id"]) for m in existing_meters}

        valid_meter_ids = [mid for mid in meter_ids if mid in existing_meter_ids]

        if valid_meter_ids:
            relationships = [
                {"user_id": user_oid, "meter_id": ObjectId(mid)}
                for mid in valid_meter_ids
            ]
            db["user_meter"].insert_many(relationships)
