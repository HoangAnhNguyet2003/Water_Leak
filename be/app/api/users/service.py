
import bcrypt as bc
from flask_jwt_extended import get_jwt
from werkzeug.exceptions import Forbidden, BadRequest , Conflict
from typing import Dict, Any
from bson import ObjectId
from .schemas import UserCreate, UserOut, UserUpdate
from . import repo
from ...extensions import get_db
import re
from types import SimpleNamespace
from bson import ObjectId
# ==== QD edited ====

def list_user_meter(user_oid: str):
    db = get_db()
    cur = db["user_meter"].find({"user_id": ObjectId(user_oid)})
    meter_ids = [repo._oid_str(c["meter_id"]) for c in cur]

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
            "id": repo._oid_str(m["_id"]),
            "branch_id": repo._oid_str(m["branch_id"]) if m.get("branch_id") else None,
            "branch_name": branch_name,
            "meter_name": m.get("meter_name"),
            "installation_time": m.get("installation_time")
        })
    return out

def list_user_all():
    """Lấy tất cả users không phân trang"""
    return repo.list_users_all()

# === End of QD edit ====

def _role_name() -> str | None:
    claims = get_jwt()
    return claims.get("role_name") if claims else None

def _hash_password(plain: str) -> str:
    return bc.hashpw(plain.encode("utf-8"), bc.gensalt()).decode("utf-8")

def _validate_password(password: str) -> bool:
    return True

def create_user_admin_only(data: UserCreate) -> UserOut:
    if _role_name() != "admin":
        raise Forbidden("Only admin can create users")

    if not _validate_password(data.password_user):
        raise BadRequest("Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character")

    role = repo.find_role_by_name(data.role_name)
    branch_oid = None
    if getattr(data, "branch_id", None):
        try:
            branch_oid = ObjectId(data.branch_id)
        except Exception:
            raise BadRequest("Invalid branch_id")
    if data.user_name is not None:
        if repo.username_taken_by_other(data.user_name):
            raise BadRequest("Username already taken")

    user = repo.insert_user(
        username=data.user_name,
        password_hash=_hash_password(data.password_user),
        role_id=role["_id"],
        is_active=getattr(data, "is_active", True),
        branch_id=branch_oid,
        last_login=getattr(data, "last_login", None),
    )

    uid = user["id"]
    if data.managed_water_meter:
        repo.update_user_meter_relationships(uid, data.managed_water_meter)

    user = repo.find_by_id(uid)
    return UserOut(
        id=user.get("id"),
        username=user.get("username"),
        is_active=user.get("is_active", True),
        branchId=repo._oid_str(user.get("branch_id")) if user.get("branch_id") else None,
    )

def get_user(uid: str):
    return repo.find_by_id(uid)

def list_user(page: int, page_size: int, q: str | None, sort: str | None, is_active: bool | None = None):
    return repo.list_users_paginated(page, page_size, q, sort, is_active)

def update_user_admin_only(user_id: str, data: UserUpdate) -> UserOut:
    print(f"Attempting to update user {user_id} with data: {data}")
    if _role_name() != "admin":
        raise Forbidden("Only admin can update users")

    updates: Dict[str, Any] = {}
    if data.user_name is not None:
        if repo.username_taken_by_other(data.user_name, user_id):
            raise BadRequest("Username already taken")
        updates["username"] = data.user_name

    if data.password_user is not None:
        if not _validate_password(data.password_user):
            raise BadRequest("Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character")
        updates["password"] = _hash_password(data.password_user)

    if data.role_name is not None:
        role = repo.find_role_by_name(data.role_name)
        updates["role_id"] = role["_id"]

    updates["branch_id"] = ObjectId(data.branch_id) if data.branch_id is not None else None

    if not updates and data.managed_water_meter is None:
        raise BadRequest("No valid fields to update")

    out = repo.update_user(user_id, updates)

    if data.managed_water_meter is not None:
        repo.update_user_meter_relationships(user_id, data.managed_water_meter)

    user = repo.find_by_id(user_id)
    managed_meters = list_user_meter(user_id)

    return UserOut(
        id=user["id"],
        username=user["username"],
        role_name=user.get("role_name"),
        branchId=repo.oid_str(user.get("branch_id")) if user.get("branch_id") else None,
        is_active=user.get("is_active", True),
    )

def remove_user(uid: str):
    return repo.delete_user(uid)
