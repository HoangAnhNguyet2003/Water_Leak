from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.require import require_role
from ...extensions import get_db
from ...utils import get_swagger_path, oid_str, find_by_id
from .prediction_utils import get_model_id_by_name, make_prediction_and_save, generate_predictions_for_date_range
from flasgger import swag_from
from ..logs.logs_routes import insert_log
from ...models.log_schemas import LogType
from datetime import datetime, timedelta, timedelta, date

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
            'confidence': confidence,
            'reconstruction_error': float(reconstruction_error),
            'threshold': float(threshold),
            'message': 'Dự đoán thành công'
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        insert_log(message=f"Error in make_prediction: {e}", log_type=LogType.ERROR, user_id=None)  
        return jsonify({"error": str(e)}), 500


@pred_bp.get("/get_lstm_autoencoder_predictions/<string:meter_id>")
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def get_lstm_autoencoder_predictions(meter_id):
    try:
        oid = ObjectId(meter_id)
        db = get_db()
        
        lstm_models = list(db.ai_models.find({
            "name": "lstm_autoencoder"
        }))
        
        if not lstm_models:
            return jsonify({"predictions": [], "message": "No LSTM models found"}), 200
            
        model_ids = [model["_id"] for model in lstm_models]
        
        all_predictions = list(db.predictions.find({
            "meter_id": oid,
            "model_id": {"$in": model_ids}
        }).sort("prediction_time", -1))
        
        daily_predictions = {}
        for pred in all_predictions:
            if hasattr(pred["prediction_time"], 'date'):
                pred_date = pred["prediction_time"].date()
            else:
                pred_datetime = datetime.fromisoformat(str(pred["prediction_time"]).replace('Z', '+00:00'))
                pred_date = pred_datetime.date()
            
            date_str = str(pred_date)
            
            if date_str not in daily_predictions:
                daily_predictions[date_str] = []
            
            score = 0
            confidence_val = str(pred.get("confidence", "")).lower()
            predicted_label = str(pred.get("predicted_label", "normal")).lower()
            
            if predicted_label == "leak":
                if confidence_val == "nnthap":
                    score = 1  
                elif confidence_val == "nntb":
                    score = 2   
                elif confidence_val == "nncao":
                    score = 3
                else:
                    score = 1
            
            daily_predictions[date_str].append({
                "original_pred": pred,
                "score": score
            })
        
        
        result_predictions = []
        for date_str, day_preds in daily_predictions.items():
            if not day_preds:
                continue
                
        
            avg_score = sum(p["score"] for p in day_preds) / len(day_preds)
            final_score = int(avg_score) 
            
         
            if final_score == 0:
                final_label = "normal"
                final_confidence = "none"
                is_anomaly = False
            elif final_score == 1:
                final_label = "leak"
                final_confidence = "NNthap"
                is_anomaly = True
            elif final_score == 2:
                final_label = "leak"  
                final_confidence = "NNTB"
                is_anomaly = True
            else:  # final_score >= 3
                final_label = "leak"
                final_confidence = "NNcao"
                is_anomaly = True
            
            template_pred = day_preds[0]["original_pred"]
            daily_result = {
                "_id": str(template_pred["_id"]),
                "meter_id": str(template_pred["meter_id"]),
                "model_id": str(template_pred["model_id"]) if template_pred.get("model_id") else None,
                "prediction_time": template_pred["prediction_time"],
                "predicted_label": final_label,
                "confidence": final_confidence,
                "is_anomaly": is_anomaly
            }
            
            for key, value in template_pred.items():
                if key not in daily_result and key not in ["_id", "meter_id", "model_id", "prediction_time", "predicted_label", "confidence", "is_anomaly"]:
                    daily_result[key] = value
            
            result_predictions.append(daily_result)
        result_predictions.sort(key=lambda x: x["prediction_time"], reverse=True)
        
        return jsonify({"predictions": result_predictions}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pred_bp.get("/get_lstm_predictions/<string:meter_id>")
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def get_lstm_predictions(meter_id):
    try:
        oid = ObjectId(meter_id)
        db = get_db()
        
        lstm_models = list(db.ai_models.find({
            "name": "lstm"
        }))
        
        if not lstm_models:
            return jsonify({"predictions": [], "message": "No LSTM model found"}), 200
            
        model_ids = [model["_id"] for model in lstm_models]
        
        # Lấy toàn bộ LSTM predictions cho meter này
        predictions = list(db.predictions.find({
            "meter_id": oid,
            "model_id": {"$in": model_ids}
        }).sort("prediction_time", -1))
        
        for pred in predictions:
            pred["_id"] = str(pred["_id"])
            pred["meter_id"] = str(pred["meter_id"])
            if pred.get("model_id"):
                pred["model_id"] = str(pred["model_id"])
        
        return jsonify({"predictions": predictions}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pred_bp.post("/generate_predictions_date_range")
@swag_from(get_swagger_path("predictions/generate_predictions_date_range.yml"))
@jwt_required()
@require_role("admin")
def generate_predictions_date_range_route():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        
        if not start_date_str or not end_date_str:
            return jsonify({"error": "start_date and end_date are required"}), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        if start_date > end_date:
            return jsonify({"error": "start_date must be before or equal to end_date"}), 400
        
        max_days = 30
        date_diff = (end_date - start_date).days + 1
        if date_diff > max_days:
            return jsonify({"error": f"Date range too large. Maximum {max_days} days allowed"}), 400
        
        prediction_result = generate_predictions_for_date_range(start_date, end_date)
        
        success_count = sum(1 for r in prediction_result["results"] if r["lstm_success"] or r["lstmae_success"])
        
        insert_log(
            f"Generated predictions for date range {start_date_str} to {end_date_str}: "
            f"{success_count}/{date_diff} days successful, "
            f"LSTM: {prediction_result['total_lstm_predictions']}, LSTM-AE: {prediction_result['total_lstmae_predictions']} predictions saved",
            LogType.INFO
        )
        
        return jsonify({
            "message": "Prediction generation completed",
            "date_range": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "total_days": date_diff
            },
            "summary": {
                "successful_days": success_count,
                "failed_days": len(prediction_result["failed_dates"]),
                "total_lstm_predictions": prediction_result["total_lstm_predictions"],
                "total_lstmae_predictions": prediction_result["total_lstmae_predictions"]
            },
            "failed_dates": prediction_result["failed_dates"],
            "detailed_results": prediction_result["results"]
        }), 200
        
    except Exception as e:
        insert_log(f"Error generating predictions for date range: {str(e)}", LogType.ERROR)
        return jsonify({"error": str(e)}), 500