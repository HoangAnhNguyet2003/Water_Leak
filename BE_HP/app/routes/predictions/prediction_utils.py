from ...models.log_schemas import LogType
from ...extensions import get_db 
from ..logs.logs_routes import insert_log
from ...models.log_schemas import LogType
from ...utils import to_object_id, oid_str
from ...ml import lstm_autoencoder_predictor 
from ...ml.lstm.predict import LSTM_Predictor
from ...ml.lstm_autoencoder.predict import LSTMAEPredictor
from ...config import MLConfig

from datetime import datetime, timedelta
from ...utils import get_vietnam_now

def get_model_id_by_name(model_name: str):
    
    db = get_db()
    model = db.ai_models.find_one({"name": model_name})
    if model:
        return model["_id"]
    return None

def make_prediction_and_save(meter_id, flow, model_name):

    db = get_db()

    is_anomaly, confidence, reconstruction_error, threshold, reconstructed_flow = lstm_autoencoder_predictor.predict_one(
        oid_str(meter_id), flow
    )

    model_id = get_model_id_by_name(model_name)
        
    insert_log(message=f"{model_name} made prediction", log_type=LogType.INFO, user_id=None)
    predicted_label = "leak" if is_anomaly else "normal"

    prediction_body = {
        "meter_id": to_object_id(meter_id),
        "model_id": model_id,
        "is_anomaly": is_anomaly,
        "prediction_time": get_vietnam_now(),
        "predicted_label": predicted_label,
        "confidence": confidence,
        "predicted_threshold": threshold,
        "recorded_instant_flow": flow,
    }

    db.predictions.insert_one(prediction_body)

    return is_anomaly, confidence, reconstruction_error, threshold, reconstructed_flow


def generate_predictions_for_date_range(start_date, end_date):
    """
    Generate predictions for a date range using both LSTM and LSTM-AE models
    """
    results = []
    total_lstm_predictions = 0
    total_lstmae_predictions = 0
    failed_dates = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        date_results = {
            "date": date_str,
            "lstm_success": False,
            "lstmae_success": False,
            "lstm_predictions": 0,
            "lstmae_predictions": 0,
            "errors": []
        }
        
        # LSTM Prediction
        try:
            lstm_predictor = LSTM_Predictor(
                historical_context=getattr(MLConfig, 'LSTM_WINDOW_CONTEXT', 4),
                model_path=getattr(MLConfig, 'LSTM_MODEL_PATH', None),
                scaler_path=getattr(MLConfig, 'SCALER_LSTM_MODEL_PATH', None),
                debug=False
            )
            
            lstm_result = lstm_predictor.predict(current_date)
            
            if lstm_result and lstm_result.get('predictions_saved', 0) > 0:
                date_results["lstm_success"] = True
                date_results["lstm_predictions"] = lstm_result['predictions_saved']
                total_lstm_predictions += lstm_result['predictions_saved']
            else:
                date_results["errors"].append("LSTM prediction failed or no predictions saved")
                
        except Exception as e:
            date_results["errors"].append(f"LSTM error: {str(e)}")
        
        # LSTM-AE Prediction
        try:
            lstmae_predictor = LSTMAEPredictor(
                historical_context=MLConfig.HISTORICAL_DATA_DAYS,
                config=MLConfig.LSTM_AE_CONFIG,
                model_path=MLConfig.LSTM_AE_MODEL_PATH,
                debug=False
            )
            
            lstmae_result = lstmae_predictor.predict(current_date)
            
            if lstmae_result and lstmae_result.get('predictions_saved', 0) > 0:
                date_results["lstmae_success"] = True
                date_results["lstmae_predictions"] = lstmae_result['predictions_saved']
                total_lstmae_predictions += lstmae_result['predictions_saved']
            else:
                date_results["errors"].append("LSTM-AE prediction failed or no predictions saved")
                
        except Exception as e:
            date_results["errors"].append(f"LSTM-AE error: {str(e)}")
        
        if not date_results["lstm_success"] and not date_results["lstmae_success"]:
            failed_dates.append(date_str)
        
        results.append(date_results)
        current_date += timedelta(days=1)
    
    return {
        "results": results,
        "total_lstm_predictions": total_lstm_predictions,
        "total_lstmae_predictions": total_lstmae_predictions,
        "failed_dates": failed_dates
    }