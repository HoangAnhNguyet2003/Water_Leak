from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..authz.require import require_role
from .service import get_meters, get_meters_simple

bp = Blueprint("user_meter", __name__)

@bp.get("/my-meters/simple")
@jwt_required()
@require_role("admin")
def get_my_meters_simple():
    uid = get_jwt_identity()
    limit = request.args.get("limit", type=int)
    items = get_meters_simple(uid, limit)
    return {"items": items}, 200

@bp.get("/<string:user_id>")
def list_for_user(user_id):
    items = get_meters(user_id)
    return {"items": items}, 200
