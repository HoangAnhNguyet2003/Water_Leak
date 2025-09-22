from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from .service import get_latest_flow, get_daily_flow
from ..authz.require import require_permissions
bp = Blueprint("measurements", __name__, url_prefix="/meters")

@bp.get("/<mid>/instant-flow")
@jwt_required()
@require_permissions("meter:read")
def latest_instant_flow(mid):
    print(f"Fetching latest instant flow for meter {mid}...")
    data = get_latest_flow(mid)
    return jsonify(data), 200

@bp.get("/<mid>/instant-flow/daily")
@jwt_required()
def daily_instant_flow(mid):
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing query param 'date' (YYYY-MM-DD)"}), 400
    data = get_daily_flow(mid, date_str)
    return jsonify(data), 200