from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

def _flatten_to_str_set(*items) -> set[str]:
    """Nhận tuple args có thể lẫn list/tuple/set và chuỗi, flatten 1–2 cấp,
    ép tất cả về str và trả về set[str]."""
    out = []
    stack = list(items)
    while stack:
        x = stack.pop()
        if x is None:
            continue
        if isinstance(x, (list, tuple, set)):
            stack.extend(x)
        else:
            out.append(str(x))
    return set(out)

def load_user_for_role_check(user_id: str):
    from .extensions import get_db
    from .utils.bson import to_object_id

    db = get_db()
    user = db.users.find_one({"_id": to_object_id(user_id)})
    if user:
        role = db.roles.find_one({"_id": user["role_id"]})
        if role:
            user["role_name"] = role["role_name"]
    return user

def require_role(*required_roles):
    """Yêu cầu user phải có một trong các role được chỉ định.
    Dùng được các kiểu:
      @require_role("admin")
      @require_role("admin", "company_manager")
      @require_role(["admin", "company_manager"])
    """
    required_set = _flatten_to_str_set(*required_roles)

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            uid = get_jwt_identity()
            user = load_user_for_role_check(uid)
            user_role = user.get("role_name") if user else None

            if user_role not in required_set:
                return jsonify({"error": {
                    "code": "FORBIDDEN",
                    "message": "Role not authorized",
                    "details": {
                        "required_roles": sorted(required_set),
                        "user_role": user_role
                    }
                }}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco