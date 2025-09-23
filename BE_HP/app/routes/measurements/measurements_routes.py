from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from ...require import require_role
from .measurement_utils import get_latest_flow, get_daily_flow
from ...utils import get_swagger_path
from flasgger import swag_from

m_bp = Blueprint("measurements", __name__)

@m_bp.get("/<mid>/instant-flow")
@swag_from(get_swagger_path('measurements/instant_flow.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def latest_instant_flow(mid):
    print(f"Fetching latest instant flow for meter {mid}...")
    data = get_latest_flow(mid)
    return jsonify(data), 200

@m_bp.get("/<mid>/instant-flow/daily")
@swag_from(get_swagger_path('measurements/daily_instant_flow.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def daily_instant_flow(mid):
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing query param 'date' (YYYY-MM-DD)"}), 400
    data = get_daily_flow(mid, date_str)
    return jsonify(data), 200