

import traceback
from flask import Blueprint, request, jsonify, make_response, current_app

from ...extensions import get_db
from flask_jwt_extended import jwt_required
from ...extensions import limiter
from ...error import BadRequest
from ...utils import json_ok, oid_str as _oid_str, get_swagger_path, get_branch_name_by_branch_id, get_role_name_by_role_id
from flasgger import swag_from
from ...require import require_role
from .user_utils import list_user_meter, remove_user, create_user_admin_only, update_user_admin_only
from pydantic import ValidationError
from ...models.user_schemas import UserCreate, UserUpdate

from werkzeug.exceptions import NotFound, Forbidden

user_bp = Blueprint("user", __name__)
from bson.errors import InvalidId


@user_bp.get("/all")
@jwt_required()
@require_role("admin", "branch_manager", "company_manager")
@swag_from(get_swagger_path('users/all.yml'))
def get_all_users():
    db = get_db()
    cur = db["users"].find({}).sort([("_id", 1)])
    result = []

    for u in cur:
        user_id = _oid_str(u["_id"])
        role_oid = _oid_str(u.get("role_id"))
        role_name = get_role_name_by_role_id(role_oid)
        managed_meters = list_user_meter(user_id)
        user_out = {
            "id": user_id,
            "username": u.get("username"),
            "roleName": role_name,
            "branchName": get_branch_name_by_branch_id(u.get("branch_id")),
            "isActive": u.get("is_active", True),
            "lastLogin": (
                            u.get("last_login").strftime("%Y-%m-%d %H:%M")
                            if u.get("last_login") is not None and hasattr(u.get("last_login"), 'strftime')
                            else u.get("last_login")
                        ),
            "managedWaterMeter": managed_meters
        }
        result.append(user_out)

    body = {
        "items": result,
        "total": len(result)
    }
    return json_ok(body)

@user_bp.delete("/delete/<string:uid>")
@jwt_required()
@require_role("admin")
@swag_from(get_swagger_path('users/delete.yml'))
def remove(uid):
    try:
        ok, reason = remove_user(uid)
    except InvalidId:
        return jsonify({"error": {"code": "BAD_ID", "message": "Invalid user id"}}), 400

    if not ok:
        if reason == "NOT_FOUND":
            return jsonify({"error": {"code": "NOT_FOUND", "message": "User not found"}}), 404
        elif reason == "FORBIDDEN":
            return jsonify({"error": {"code": "FORBIDDEN", "message": "Cannot delete admin account"}}), 403
        else:
            return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Unexpected error"}}), 500

    return jsonify({"status": "ok"}), 200

@user_bp.post("/add")
@jwt_required()
@require_role("admin")
@swag_from(get_swagger_path('users/add.yml'))
def create_user():
    try:
        payload_json = request.get_json(force=True)
        payload = UserCreate(**payload_json)
    except ValidationError as e:
        return jsonify({"error": "ValidationError", "details": e.errors()}), 422
    except Exception as e:
        return jsonify({"error": "BadRequest", "message": "Invalid request payload"}), 400

    try:
        user = create_user_admin_only(payload)
        user_out = {
            "id": _oid_str(user.id),
            "branchId": _oid_str(user.branchId),
            "username": user.username,
            "is_active": user.is_active,
        }
        return jsonify(user_out), 201

    except BadRequest as e:
        return jsonify({"error": "BadRequest", "message": str(e)}), 400
    except Forbidden as e:
        return jsonify({"error": "Forbidden", "message": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e), "message": "Failed to create user"}), 500
    
@user_bp.patch("/update/<string:uid>")
@jwt_required()
@require_role("admin")
@swag_from(get_swagger_path('users/update.yml'))
def update_user(uid):
    print(f"Updating user {uid}...")
    try:
        print("Parsed update data:", request.get_json())
        payload = UserUpdate(**request.get_json(force=True))
    except ValidationError as e:
        print(traceback.format_exc())
        return jsonify({"error": "ValidationError", "details": e.errors()}), 422

    try:
        user = update_user_admin_only(uid, payload)
        user_out = {
            "id": user.id,
            "username": user.username,
            "roleName": user.role_name,
            "isActive": user.is_active,
        }
        return jsonify(user_out), 200
    except BadRequest as e:
        return jsonify({"error": "BadRequest", "message": str(e)}), 400
    except NotFound:
        return jsonify({"error": "NotFound", "message": "User not found"}), 404
    except Exception as e:
        print(f"Error updating user {uid}: {e}")
        return jsonify({"error": "InternalError", "message": "Failed to update user"}), 500

