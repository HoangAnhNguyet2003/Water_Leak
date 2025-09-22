from flask import Blueprint, request, jsonify, make_response, current_app   
from flask_jwt_extended import get_csrf_token,create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from .schemas import  LoginIn, UserPublic
from .service import  validate_login
from ...errors import BadRequest
from ..common.response import json_ok
from ...extensions import get_db, limiter
from bson import ObjectId
import bcrypt as bc
from ...extensions import TOKEN_BLOCKLIST
import traceback
from datetime import datetime
import logging 

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="auth")

@bp.post("/role-based-login")
@limiter.limit("10 per minute")
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

        response = make_response(json_ok(response_data))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        logger.info(f"{user_info['username']} Đăng nhập thành công")
        return response

    except Exception as e:
        logger.error(f"Đăng nhập thất bại cho {request.json.get('username')}: {e}")
        traceback.print_exc()
        raise e

@bp.post("/refresh")
@jwt_required(refresh=True, locations=["cookies"])
def refresh():
    uid = get_jwt_identity()
    current_claims = get_jwt()

    db = get_db()
    user = db.users.find_one({"_id": ObjectId(uid), "is_active": True})
    if not user:
        logger.warning(f"Refresh token cho người dùng không bị vô hiệu hóa/đã xóa: {uid}")
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

    set_access_cookies(
        response,
        new_access_token,
        domain=current_app.config.get("JWT_COOKIE_DOMAIN", None),
        secure=current_app.config["JWT_COOKIE_SECURE"],
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        httponly=True
    )

    logger.info(f"Token refreshed for user {uid}")
    return response

@bp.post("/logout")
def logout():
    """
    Logout endpoint - clears cookies and blocklist tokens
    """
    jti = None
    try:
        try:
            jti = get_jwt().get("jti")
            if jti:
                TOKEN_BLOCKLIST.add(jti)
                logger.info(f"Access token {jti} added to blocklist")
        except Exception as e:
            logger.warning(f"Could not get access token JTI: {e}")

        response = make_response(jsonify({
            "msg": "Logout thành công",
            "message": "Đăng xuất thành công",
            "timestamp": str(datetime.now())
        }))

        cookies_to_clear = [
            'access_token', 'csrf_access_token',
            'refresh_token', 'csrf_refresh_token'
        ]
        for cookie in cookies_to_clear:
            response.set_cookie(
                cookie, '', expires=0,
                httponly=True, samesite='Strict', secure=False
            )

        try:
            unset_jwt_cookies(response)
        except Exception as e:
            logger.error(f"Error unsetting JWT cookies: {e}")

        if jti:
            logger.info(f"User logged out, token JTI: {jti}")
        else:
            logger.info("User logged out (token not available)")

        return response

    except Exception as e:
        logger.error(f"Logout error: {e}")
        response = make_response(jsonify({
            "error": str(e),
            "msg": "Logout attempted - cookies cleared",
            "message": "Đăng xuất thành công - cookies đã được xóa"
        }), 200)  

        response.set_cookie('access_token', '', expires=0, httponly=True, samesite='Strict', secure=False)
        response.set_cookie('refresh_token', '', expires=0, httponly=True, samesite='Strict', secure=False)

        try:
            unset_jwt_cookies(response)
        except:
            pass

        return response

@bp.get("/me")
@jwt_required()
def get_current_user():
    try:
        uid = get_jwt_identity()
        claims = get_jwt()

        db = get_db()
        user = db.users.find_one({"_id": ObjectId(uid), "is_active": True})
        if not user:
            logger.warning(f"Cố sử dụng /me cho người dùng đã bị vô hiệu hóa/đã xóa: {uid}")
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
        logger.error(f"Error in /me: {e}")
        return jsonify({
            "message": "Lấy thông tin người dùng thất bại",
            "authenticated": False,
            "error": str(e)
        }), 401

