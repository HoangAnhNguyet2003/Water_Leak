from flask import Blueprint, request, jsonify, make_response, current_app
from flasgger import swag_from
from bson import ObjectId
from flask_jwt_extended import get_csrf_token,create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from datetime import datetime

from ...extensions import get_db
from ...extensions import limiter
from ...models.auth_schemas import LoginIn
from .auth_utils import validate_login
from ...error import BadRequest
from ...utils import json_ok, get_swagger_path
from ...extensions import TOKEN_BLOCKLIST
from ...routes.logs.log_utils import insert_log
from ...models.log_schemas import LogType
from ...utils.logging import log_api

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/role-based-login")
@limiter.limit("10 per minute")
@swag_from(get_swagger_path('auth/role_based_login.yml'))
def role_based_login():
    """
    Role-based login endpoint
    """
    try:
        data = LoginIn(**(request.get_json(silent=True) or {}))
    except Exception as e:
        raise BadRequest(str(e))

    try:
        user_info = validate_login(data)

        claims = {
            "username": user_info["username"],
            "role_id": user_info["role_id"],
            "role_name": user_info["role_name"],
            "company_id": user_info["company_id"],
            "branch_id": user_info["branch_id"]
        }

        access_token = create_access_token(identity=user_info["id"], additional_claims=claims)
        refresh_token = create_refresh_token(identity=user_info["id"], additional_claims=claims)

        response_data = {
            "message": "Đăng nhập thành công",
            "user": {
                "id": user_info["id"],
                "username": user_info["username"],
                "roleId": user_info["role_id"],
                "roleName": user_info["role_name"],
                "companyId": user_info["company_id"],
                "branchId": user_info["branch_id"]
            }
        }
        try:
            db = get_db()
            db.users.update_one({"_id": ObjectId(user_info["id"])}, {"$set": {"last_login": datetime.now()}})
        except Exception:
            pass

        insert_log(message=response_data["message"], log_type=LogType.INFO, user_id=user_info["id"])
        response = make_response(json_ok(response_data))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        return response

    except Exception as e:
        insert_log(message=f"Đăng nhập thất bại cho {data.username}: {str(e)}", log_type=LogType.ERROR)
        raise e
    

@auth_bp.post("/refresh")
@jwt_required(refresh=True, locations=["cookies"])
@swag_from(get_swagger_path('auth/refresh.yml'))
@log_api(log_type=LogType.INFO, message="Refresh token đăng nhập")
def refresh():
    uid = get_jwt_identity()
    current_claims = get_jwt()

    db = get_db()
    user = db.users.find_one({"_id": ObjectId(uid), "is_active": True})
    if not user:
        return jsonify({
            "message": "Tài khoản không tồn tại hoặc đã bị khóa",
            "authenticated": False
        }), 401

    new_access_token = create_access_token(
        identity=uid,
        additional_claims={
            "username": current_claims.get("username"),
            "role_id": current_claims.get("role_id"),
            "role_name": current_claims.get("role_name"),
            "company_id": current_claims.get("company_id"),
            "branch_id": current_claims.get("branch_id")
        }
    )

    csrf_token = get_csrf_token(new_access_token)
    db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"last_login": datetime.now()}})
    
    response = make_response(json_ok({
        "message": "Token đã được làm mới thành công",
        "user": {
            "id": uid,
            "username": current_claims.get("username"),
            "roleId": current_claims.get("role_id"),
            "roleName": current_claims.get("role_name"),
            "companyId": current_claims.get("company_id"),
            "branchId": current_claims.get("branch_id")
        },
        "csrf_access_token": csrf_token
    }))
    insert_log(message="Token đã được làm mới thành công", log_type=LogType.INFO, user_id=uid)
    set_access_cookies(
        response,
        new_access_token,
        domain=current_app.config.get("JWT_COOKIE_DOMAIN", None),
        secure=current_app.config["JWT_COOKIE_SECURE"],
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        httponly=True
    )

    return response

@auth_bp.post("/logout")
@jwt_required(optional=True)  
@swag_from(get_swagger_path('auth/logout.yml'))
def logout():
    uid = None
    jti = None
    try:
        uid = get_jwt_identity()
        jti = get_jwt().get("jti")

        if jti:
            TOKEN_BLOCKLIST.add(jti)

        response = make_response(jsonify({
            "msg": "Logout thành công",
            "message": "Đăng xuất thành công",
            "timestamp": str(datetime.now())
        }))

        insert_log(message="User đăng xuất thành công", log_type=LogType.INFO, user_id=uid)

        cookies_to_clear = [
            'access_token', 'csrf_access_token',
            'refresh_token', 'csrf_refresh_token'
        ]
        for cookie in cookies_to_clear:
            response.set_cookie(
                cookie, '', expires=0,
                httponly=True, samesite='Strict', secure=False
            )

        unset_jwt_cookies(response)
        return response

    except Exception as e:
        print(f"Logout error: {e}")

        response = make_response(jsonify({
            "error": str(e),
            "msg": "Logout attempted - cookies cleared",
            "message": "Đăng xuất thành công - cookies đã được xóa"
        }), 200)

        insert_log(message="User đăng xuất (không có token)", log_type=LogType.INFO, user_id=uid)

        unset_jwt_cookies(response)
        return response


@auth_bp.get("/me")
@jwt_required()
@swag_from(get_swagger_path('auth/me.yml'))
def get_current_user():
    try:
        uid = get_jwt_identity()
        claims = get_jwt()

        db = get_db()
        user = db.users.find_one({"_id": ObjectId(uid), "is_active": True})
        if not user:
            print(f"Cố sử dụng /me cho người dùng đã bị vô hiệu hóa/đã xóa: {uid}")
            return jsonify({
                "message": "Tài khoản không tồn tại hoặc đã bị khóa",
                "authenticated": False
            }), 401

        return json_ok({
            "message": "Lấy thông tin người dùng thành công",
            "id": uid,
            "username": claims.get("username"),
            "roleId": claims.get("role_id"),
            "roleName": claims.get("role_name"),
            "companyId": claims.get("company_id"),
            "branchId": claims.get("branch_id"),
            "authenticated": True
        })
    except Exception as e:
        print(f"Error in /me: {e}")
        return jsonify({
            "message": "Lấy thông tin người dùng thất bại",
            "authenticated": False,
            "error": str(e)
        }), 401

