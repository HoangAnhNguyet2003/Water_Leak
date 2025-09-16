import bcrypt as bc
from flask_jwt_extended import get_jwt_identity
from flask import jsonify
from bson import ObjectId
from ...extensions import get_db

def _get_user_by_id(user_id: str):
    db = get_db()
    return db.users.find_one({"_id": ObjectId(user_id)})

def validate_current_user_password(plain_password: str):
    """
    Kiểm tra mật khẩu của *user đang đăng nhập* (từ JWT).
    Trả về (ok: bool, error_response | None, user_doc | None)
    """
    if not plain_password:
        return False, jsonify({"success": False, "error": "Password is required"}), None

    uid = get_jwt_identity()
    if not uid:
        return False, jsonify({"success": False, "error": "Unauthorized"}), None

    user = _get_user_by_id(uid)
    if not user:
        return False, jsonify({"success": False, "error": "User not found"}), None

    # user["password"] là chuỗi hash đã lưu (bcrypt)
    try:
        ok = bc.checkpw(plain_password.encode("utf-8"), user["password"].encode("utf-8"))
    except Exception:
        ok = False

    if not ok:
        return False, jsonify({"success": False, "error": "Invalid password"}), None

    return True, None, user
