from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.require import require_role
from ...extensions import get_db
from ...utils import get_swagger_path
from flasgger import swag_from


pred_bp = Blueprint("predictions", __name__)

@pred_bp.get("/get_all_predictions_by_meter_id/manual/<string:mid>")
@swag_from(get_swagger_path('predictions/manual_predictions.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def get_all_predictions_by_meter_id(mid):
    try:
        oid = ObjectId(mid)
    except Exception:
        return jsonify({"error": "Invalid meter id"}), 400

    try:
        db = get_db()
        predictions = db["predictions"].find({"meter_id": oid, "model_id": None})
        result = [p for p in predictions]
        return jsonify(result), 200
    except Exception as e:
        print(f"DB error in get_all_predictions_by_meter_id: {e}")
        return jsonify({"error": "Internal server error"}), 500

@pred_bp.get("/get_all_predictions_by_meter_id/deep_learning/<string:mid>")
@swag_from(get_swagger_path('predictions/deep_learning_predictions.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def get_all_predictions_by_meter_id_deep_learning(mid):
    try:
        oid = ObjectId(mid)
    except Exception:
        return jsonify({"error": "Invalid meter id"}), 400

    try:
        db = get_db()
        predictions = db["predictions"].find({"meter_id": oid})
        result = [p for p in predictions]
        return jsonify(result), 200
    except Exception as e:
        print(f"DB error in get_all_predictions_by_meter_id_deep_learning: {e}")
        return jsonify({"error": "Internal server error"}), 500