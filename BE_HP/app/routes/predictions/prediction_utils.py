from ...models.log_schemas import LogType
from ...extensions import get_db 
from ..logs.logs_routes import insert_log
from ...models.log_schemas import LogType
from ...utils import to_object_id, oid_str
from ...ml import lstm_autoencoder_predictor 

from datetime import datetime

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
        "prediction_time": datetime.now(),
        "predicted_label": predicted_label,
        "confidence": confidence,
        "predicted_threshold": threshold,
        "recorded_instant_flow": flow,
    }

    db.predictions.insert_one(prediction_body)

    return is_anomaly, confidence, reconstruction_error, threshold, reconstructed_flow