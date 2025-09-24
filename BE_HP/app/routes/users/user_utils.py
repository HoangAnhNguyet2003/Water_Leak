


from typing import Any, Dict
from bson import ObjectId
from pymongo import ReturnDocument
from werkzeug.exceptions import Forbidden, BadRequest, NotFound

from app.models.user_schemas import UserCreate, UserOut, UserUpdate
from ...extensions import get_db
from ...utils import oid_str as _oid_str, get_role_name_by_role_id, to_object_id, find_by_id, hash_password as _hash_password, role_name as _role_name
from bson.errors import InvalidId

COL = "users"

# ------------------- Helper to get current user's role name ------------------- 
    
def _validate_password(password: str) -> bool:
    return len(password) >= 6

def username_taken_by_other(user_name: str, exclude_user_id: str = None) -> bool:
    db = get_db()
    query = {"username": user_name}
    if exclude_user_id:
        query["_id"] = {"$ne": ObjectId(exclude_user_id)}
    return db[COL].find_one(query) is not None

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

def find_role_by_name(role_name: str) -> Dict[str, Any]:
    db = get_db()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        raise NotFound(f"Role '{role_name}' not found")
    return role

# ------------------- User API helpers -------------------
def list_user_meter(user_oid: str):
    db = get_db()
    cur = db["user_meter"].find({"user_id": ObjectId(user_oid)})
    meter_ids = [_oid_str(c["meter_id"]) for c in cur]

    if not meter_ids:
        return []

    meters = db["meters"].find({"_id": {"$in": [ObjectId(mid) for mid in meter_ids]}})
    out = []
    for m in meters:
        branch_name = None
        if m.get("branch_id"):
            branch = db["branches"].find_one({"_id": m["branch_id"]})
            branch_name = branch.get("name") if branch else None

        out.append({
            "id": _oid_str(m["_id"]),
            "branch_id": _oid_str(m["branch_id"]) if m.get("branch_id") else None,
            "branch_name": branch_name,
            "meter_name": m.get("meter_name"),
            "installation_time": m.get("installation_time")
        })
    return out

def remove_user(uid: str):
    db = get_db()
    try:
        obj_id = to_object_id(uid)
    except InvalidId:
        raise

    try:
        user = db["users"].find_one({"_id": obj_id})
        if not user:
            return False, "NOT_FOUND"

        if get_role_name_by_role_id(_oid_str(user.get("role_id"))) == "admin":
            return False, "FORBIDDEN"

        res = db["users"].delete_one({"_id": obj_id})
        if res.deleted_count != 1:
            return False, "NOT_FOUND"

        db["user_meter"].delete_many({"user_id": obj_id})

        return True, ""
    except Exception as e:
        return False, "ERROR"

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

def update_user_admin_only(user_id: str, data: UserUpdate) -> UserOut:
    print(f"Attempting to update user {user_id} with data: {data}")
    if _role_name() != "admin":
        raise Forbidden("Only admin can update users")

    updates: Dict[str, Any] = {}
    if data.user_name is not None:
        if username_taken_by_other(data.user_name, user_id):
            raise BadRequest("Username already taken")
        updates["username"] = data.user_name

    if data.password_user is not None:
        if not _validate_password(data.password_user):
            raise BadRequest("Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character")
        updates["password"] = _hash_password(data.password_user)

    if data.role_name is not None:
        role = find_role_by_name(data.role_name)
        updates["role_id"] = role["_id"]

    updates["branch_id"] = ObjectId(data.branch_id) if data.branch_id is not None else None

    if not updates and data.managed_water_meter is None:
        raise BadRequest("No valid fields to update")

    out = update_user(user_id, updates)

    if data.managed_water_meter is not None:
        update_user_meter_relationships(user_id, data.managed_water_meter)

    user = find_by_id(user_id, COL)
    managed_meters = list_user_meter(user_id)

    return UserOut(
        id=user["id"],
        username=user["username"],
        role_name=user.get("role_name"),
        branchId=_oid_str(user.get("branch_id")) if user.get("branch_id") else None,
        is_active=user.get("is_active", True),
    )

def create_user_admin_only(data: UserCreate) -> UserOut:
    if _role_name() != "admin":
        raise Forbidden("Only admin can create users")

    if not _validate_password(data.password_user):
        raise BadRequest("Password must be at least 6 characters long")

    role = find_role_by_name(data.role_name)
    branch_oid = None
    if getattr(data, "branch_id", None):
        try:
            branch_oid = ObjectId(data.branch_id)
        except Exception:
            raise BadRequest("Invalid branch_id")
    if data.user_name is not None:
        if username_taken_by_other(data.user_name):
            raise BadRequest("Username already taken")

    user = insert_user(
        username=data.user_name,
        password_hash=_hash_password(data.password_user),
        role_id=role["_id"],
        is_active=getattr(data, "is_active", True),
        branch_id=branch_oid,
        last_login=getattr(data, "last_login", None),
    )

    uid = user["id"]
    if data.managed_water_meter:
        update_user_meter_relationships(uid, data.managed_water_meter)

    user = find_by_id(uid, COL)
    return UserOut(
        id=user.get("id"),
        username=user.get("username"),
        is_active=user.get("is_active", True),
        branchId=_oid_str(user.get("branch_id")) if user.get("branch_id") else None,
    )
