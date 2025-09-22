from ..authz.repo import load_permissions_for_user
from .schemas import  LoginIn
from . import repo
from ...errors import BadRequest, Conflict
from ...utils.security import hash_password, verify_password
from ...utils.bson import oid_str
import logging

logger = logging.getLogger(__name__)

def validate_login(data: LoginIn):
    user = repo.get_user_by_username(data.username)
    if not user:
        logger.warning(f"Không tồn tại username: {data.username}")
        raise BadRequest("Tài khoản hoặc mật khẩu không đúng!")

    if not verify_password(data.password, user.get("password", "")):
        logger.warning(f"Mật khẩu không hợp lệ cho người dùng: {data.username}")
        raise BadRequest("Mật khẩu không hợp lệ cho người dùng")

    if not user.get("is_active", True):
        logger.warning(f"Tài khoản đã bị vô hiệu hóa: {data.username}")
        raise BadRequest("Tài khoản đã bị vô hiệu hóa")

    role_id = user.get("role_id")
    role_name = None
    if role_id:
        role = repo.get_role(role_id)
        role_name = role.get("role_name") if role else None

    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "role_id": str(role_id) if role_id else None,
        "role_name": role_name,
        "company_id": str(user.get("company_id")) if user.get("company_id") else None,
        "branch_id": str(user.get("branch_id")) if user.get("branch_id") else None,
    }
