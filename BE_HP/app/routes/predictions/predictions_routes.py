from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.require import require_role
from ...extensions import get_db
from ...utils import get_swagger_path, oid_str, find_by_id
from .prediction_utils import get_model_id_by_name, make_prediction_and_save
from flasgger import swag_from
from ..logs.logs_routes import insert_log
from ...models.log_schemas import LogType

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
    

@pred_bp.post("/make_prediction")
@swag_from(get_swagger_path('predictions/make_prediction.yml'))
def make_prediction(): 
    
    try: 
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dữ liệu đầu vào không hợp lệ"}), 400
            
        if 'meter_id' not in data or 'flow_rate' not in data:
            return jsonify({"error": "Thiếu trường bắt buộc"}), 400
        
        meter_id = data['meter_id']
        flow_rate = data['flow_rate']

        meter = find_by_id(oid_str(meter_id), 'meters')
        if not meter: 
            return jsonify({"error": "Không tìm thấy đồng hồ tương ứng"}), 400
        
        is_anomaly, confidence, reconstruction_error, threshold, reconstructed_flow = make_prediction_and_save(
            meter_id, flow_rate, model_name="lstm_autoencoder"
        )

        response_data = {
            'meter_id': oid_str(meter_id), 
            'flow': float(flow_rate),
            'reconstructed_flow': float(reconstructed_flow),
            'is_anomaly': bool(is_anomaly),
            'confidence': float(confidence),
            'reconstruction_error': float(reconstruction_error),
            'threshold': float(threshold),
            'message': 'Dự đoán thành công'
        }
        
        print(f"Response data: {response_data}")  
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error in manual_prediction: {e}")
        insert_log(message=f"Error in make_prediction: {e}", log_type=LogType.ERROR, user_id=None)  
        return jsonify({"error": str(e)}), 500