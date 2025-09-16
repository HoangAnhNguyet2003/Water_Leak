from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from .schemas import  LoginIn, UserPublic
from .service import  validate_login, validate_jwt_login
from ...errors import BadRequest
from ..common.response import json_ok
from ...extensions import get_db, limiter
from bson import ObjectId
import bcrypt as bc
from ...extensions import TOKEN_BLOCKLIST
import traceback
from datetime import datetime

bp = Blueprint("auth", __name__, url_prefix="auth")
# === QD edited ====
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
        user_info = validate_jwt_login(data)

        claims = {
            "username": user_info["username"],
            "role_id": user_info["role_id"],
            "role_name": user_info.get("role_name"),
            "company_id": user_info["company_id"],
            "branch_id": user_info["branch_id"]
        }

        access_token = create_access_token(
            identity=user_info["id"], 
            additional_claims=claims
        )
        refresh_token = create_refresh_token(
            identity=user_info["id"],
            additional_claims=claims
        )

        response_data = {
            "message": "Đăng nhập thành công",
            "token": access_token,
            "refreshToken": refresh_token,
            "roleId": user_info["role_id"],
            "user": {
                "id": user_info["id"],
                "username": user_info["username"],
                "roleId": user_info["role_id"],
                "roleName": user_info.get("role_name")
            }
        }
        
        response = make_response(json_ok(response_data))
        
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        
        return response

    except Exception as e:
        traceback.print_exc()
        raise e

@bp.post("/refresh")
@jwt_required(refresh=True, locations=["cookies"])
def refresh():
    uid = get_jwt_identity()
    current_claims = get_jwt()
    
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

    response = make_response(json_ok({
        "message": "Token đã được làm mới thành công",
        "token": new_access_token,
        "roleId": current_claims.get("role_id")
    }))

    set_access_cookies(response, new_access_token, domain='localhost')

    return response

@bp.post("/logout")
def logout():
    """
    Logout endpoint - clears cookies regardless of token validity
    """
    try:
        try:
            jti = get_jwt()["jti"]
            TOKEN_BLOCKLIST.add(jti)
            print(f"✅ Token {jti} added to blocklist")
        except Exception as jwt_error:
            print(f"⚠️  JWT token invalid or missing: {jwt_error}")
          
        response = make_response(jsonify({
            "msg": "Logout thành công",
            "message": "Đăng xuất thành công",
            "timestamp": str(datetime.now())
        }))

        response.set_cookie('access_token', '', expires=0,
                           httponly=True, samesite='Strict', secure=False)
        response.set_cookie('csrf_access_token', '', expires=0,
                           httponly=True, samesite='Strict', secure=False)
        response.set_cookie('refresh_token', '', expires=0,
                           httponly=True, samesite='Strict', secure=False)
        response.set_cookie('csrf_refresh_token', '', expires=0,
                           httponly=True, samesite='Strict', secure=False)

        try:
            unset_jwt_cookies(response)
        except Exception as unset_error:
            print(f"⚠️  Error unsetting JWT cookies: {unset_error}")

        print("✅ Logout successful - cookies cleared")
        return response

    except Exception as e:
        print(f"❌ Logout error: {e}")
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
    """
    Get current user information from JWT token
    Returns user data from JWT claims for frontend authentication
    """
    try:
        uid = get_jwt_identity()
        claims = get_jwt()
        
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
        return jsonify({
            "message": "Lấy thông tin người dùng thất bại",
            "authenticated": False, 
            "error": str(e)
        }), 401
    
# ===== End QD edited =====

