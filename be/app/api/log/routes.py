from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from .service import get_logs_scoped, delete_log_scoped
from ..authz.require import require_permissions, require_password_confirmation
from pydantic import ValidationError
from .schemas import LogCreate
from .service import create_log_scoped

bp = Blueprint("logs", __name__, url_prefix="/logs")

@bp.get("/")
@jwt_required()
@require_permissions("log:read")
def list_logs_api():
    print("Listing logs...")
    page  = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    sort  = request.args.get("sort", "created_time", type=str)  
    order = request.args.get("order", "desc", type=str)

    data = get_logs_scoped(page=page, limit=limit, sort=sort, order=order)
    return jsonify(data), 200

@bp.delete("/<log_id>")
@require_password_confirmation()
@require_permissions("log:delete")
@jwt_required()  
def delete_log(log_id):
    delete_log_scoped(log_id)
    return jsonify({"status": "ok"}), 200

@bp.post("")
@jwt_required()
@require_password_confirmation()
@require_permissions("log:create")
def create_log():
    data = request.get_json(silent=True) or {}
    try:
        payload = LogCreate(**data)
    except ValidationError as e:
        return jsonify({"error":"ValidationError","details":e.errors()}), 422

    log_out = create_log_scoped(payload)
    return jsonify(log_out.model_dump()), 201