from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from ...extensions import get_db
from ..authz.require import require_role
from ...errors import BadRequest
from ..common.response import json_ok, created, no_content
from ..common.pagination import parse_pagination, build_links
from ...utils.time_utils import day_bounds_utc
import traceback

bp = Blueprint("predictions", __name__, url_prefix="meters")

@bp.get("/get_all_predictions_by_meter_id/manual/<string:mid>")
@jwt_required()
@require_role("branch_manager", "company_manager")
def get_all_predictions_by_meter_id(mid):
    db = get_db()
    predictions = db["predictions"].find(
        {"meter_id": ObjectId(mid)}
    )   
        
    return jsonify([p for p in predictions]), 200

@bp.get("/get_all_predictions_by_meter_id/deep_learning/<string:mid>")
@jwt_required()
@require_role("branch_manager", "company_manager")
def get_all_predictions_by_meter_id_deep_learning(mid):
    db = get_db()
    predictions = db["predictions"].find(
        {"meter_id": ObjectId(mid)},
        {"model": "deep_learning"}
    )
    return jsonify([p for p in predictions]), 200