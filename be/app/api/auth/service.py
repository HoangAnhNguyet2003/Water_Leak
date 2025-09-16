from ..authz.repo import load_permissions_for_user
from .schemas import  LoginIn
from . import repo
from ...errors import BadRequest, Conflict
from ...utils.security import hash_password, verify_password
from ...utils.bson import oid_str

def validate_jwt_login(data: LoginIn):
    user = repo.get_user_by_username(data.username)
    
    if not user:
        raise BadRequest("Invalid username or password")
    
    if not verify_password(data.password, user.get("password", "")):
        raise BadRequest("Invalid username or password")
    
    if not user.get("is_active", True):
        raise BadRequest("User account is disabled")
    
    role = repo.get_role(user.get("role_id"))
    
    return {
        "id": str(user["id"]),
        "username": user.get("username"),
        "role_id": str(user["role_id"]) if user.get("role_id") else None,
        "role_name": role["role_name"] if role else None,
        "company_id": str(user["company_id"]) if user.get("company_id") else None,
        "branch_id": str(user["branch_id"]) if user.get("branch_id") else None,
    }

def validate_login(data: LoginIn):
    user = repo.get_user_by_username(data.username)
    print("User from DB:", user)
    if not user or not verify_password(data.password, user.get("password", "")):
        raise BadRequest("Invalid username or password")
    if not user.get("is_active", True):
        raise BadRequest("User disabled")
    role = repo.get_role(user.get("role_id"))
    print("User role:", role)
    perms = load_permissions_for_user(user["id"])
    return {
        "id": str(user["id"]),
        "username": user.get("username"),
        "role_id": str(user["role_id"]) if user.get("role_id") else None,
        "role_name": role["role_name"] if role else None,
        "permissions": list(perms),
        "company_id": str(user["company_id"]) if user.get("company_id") else None,
        "branch_id": str(user["branch_id"]) if user.get("branch_id") else None,
    }
