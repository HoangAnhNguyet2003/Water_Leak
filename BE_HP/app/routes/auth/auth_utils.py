from ...models.auth_schemas import LoginIn
from ...extensions import get_db
from ...error import BadRequest
from ...utils import verify_password, oid_str, get_role_by_role_id

def get_user_by_username(username: str):
    db = get_db()
    u = db.users.find_one({"username": username})
    if not u: return None
    u["_id"] = oid_str(u.pop("_id"))

    return u
def validate_login(data: LoginIn):
    user = get_user_by_username(data.username)
    if not user:
        raise BadRequest("Tài khoản hoặc mật khẩu không đúng!")

    if not verify_password(data.password, user.get("password", "")):
        raise BadRequest("Mật khẩu không hợp lệ cho người dùng")

    if not user.get("is_active", True):
        raise BadRequest("Tài khoản đã bị vô hiệu hóa")

    role_id = user.get("role_id")
    role_name = None
    if role_id:
        role = get_role_by_role_id(role_id)
        role_name = role.get("role_name") if role else None

    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "role_id": str(role_id) if role_id else None,
        "role_name": role_name,
        "company_id": str(user.get("company_id")) if user.get("company_id") else None,
        "branch_id": str(user.get("branch_id")) if user.get("branch_id") else None,
    }    