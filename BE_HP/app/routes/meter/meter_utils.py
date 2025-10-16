# create_meter_admin_only, get_meters_list, list_meters, remove_meter, build_leak_overview
from datetime import datetime, timedelta, timezone
from email import errors
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from bson import ObjectId

from ...models.meter_schema import MeterCreate, MeterOut
from ...utils import get_vietnam_now, VIETNAM_TZ
from werkzeug.exceptions import BadRequest, Conflict, Forbidden
from ...utils import role_name as _role_name, find_branch_by_name, oid_str, get_user_scope, to_object_id
from ...extensions import get_db

COL = "meters"

def get(mid: str) -> Optional[Dict[str, Any]]:
    d = get_db()[COL].find_one({"_id": to_object_id(mid)})
    if not d:
        return None
    d["id"] = oid_str(d.pop("_id"))
    d["branch_id"] = oid_str(d["branch_id"])
    return d

def exists_meter(meter_id: str) -> bool:
    db = get_db()
    return db[COL].find_one({"meter_id": meter_id}) is not None

def _meter_id_from_name(meter_name: str) -> str:
    return hashlib.md5(meter_name.strip().encode("utf-8")).hexdigest()

def _branch_ids_in_company(company_id):
    db = get_db()
    return [oid_str(b["_id"]) for b in db.branches.find({"company_id": company_id}, {"_id":1})]

def list_meter_paginated(page:int, page_size:int, branch_ids: Optional[list[str]], q: Optional[str], sort: Optional[str]) -> Tuple[List[Dict[str,Any]], bool]:
    db = get_db()
    flt: Dict[str, Any] = {}
    if branch_ids:
        flt["branch_id"] = {"$in": [to_object_id(x) for x in branch_ids]}
    if q:
        flt["meter_name"] = {"$regex": q, "$options": "i"}

    srt = [("_id",1)]
    if sort:
        field = sort.lstrip("-"); direc = -1 if sort.startswith("-") else 1
        srt = [(field, direc)]

    skip = (page-1) * page_size
    cur = db[COL].find(flt).sort(srt).skip(skip).limit(page_size+1)

    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        d["branch_id"] = oid_str(d["branch_id"])
        out.append(d)
    has_next = len(out) > page_size
    if has_next: out = out[:page_size]
    return out, has_next

def list_meters(page:int, page_size:int, q: Optional[str], sort: Optional[str]):
    company_id, branch_id, role_id, role_name = get_user_scope()
    if branch_id:
        return list_meter_paginated(page, page_size, [oid_str(branch_id)], q, sort)
    if company_id:
        branches = _branch_ids_in_company(company_id)
        return list_meter_paginated(page, page_size, branches, q, sort)
    # admin: không giới hạn
    return list_meter_paginated(page, page_size, None, q, sort)

def insert_meter(branch_id: ObjectId, meter_name: str, installation_time: Optional[datetime]) -> Dict[str, Any]:
    db = get_db()
    meter_id = _meter_id_from_name(meter_name)

    if exists_meter(meter_id):
        raise Conflict("Meter already exists in this branch")

    doc = {
        "branch_id": branch_id,
        "meter_id": meter_id,
        "meter_name": meter_name.strip(),
        "installation_time": installation_time or get_vietnam_now(),
    }
    try:
        res = db[COL].insert_one(doc)
    except errors.DuplicateKeyError as e:
        # Nếu 2 request song song, unique index sẽ chặn ở đây
        raise ("Meter already exists in this branch") from e

    return {
        "id": str(res.inserted_id),
        "branch_id": str(branch_id),
        "meter_id": meter_id,
        "meter_name": doc["meter_name"],
        "installation_time": doc["installation_time"].isoformat(),
    }

def create_meter_admin_only(data: MeterCreate) -> MeterOut:
    if _role_name() != "admin":
        raise Forbidden("Only admin can create meter")
    branch = find_branch_by_name(data.branch_name)

    if exists_meter(_meter_id_from_name(data.meter_name)):
        raise Conflict(f"Meter '{data.meter_name}' already exists")

    doc = insert_meter(branch["_id"], data.meter_name, data.installation_time)
    doc["branch_name"] = branch["name"]
    return MeterOut(**doc)



def get_meters_list(date_str: str | None = None):
    db = get_db()

    if not date_str:
        date_str = get_vietnam_now().strftime("%Y-%m-%d")

    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_vn = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=VIETNAM_TZ)
    end_vn   = start_vn + timedelta(days=1)

    pipeline = [
        {
            "$lookup": {
                "from": "branches",
                "localField": "branch_id",
                "foreignField": "_id",
                "as": "branch"
            }
        },
        {"$unwind": "$branch"},
        {
            "$lookup": {
                "from": "predictions",                 
                "let": {"mid": "$_id"},
                "pipeline": [
                    { 
                        "$match": { 
                            "$expr": { "$eq": ["$meter_id", "$$mid"] },
                            "prediction_time": {"$gte": start_vn, "$lt": end_vn}
                        } 
                    },
                    { "$sort": { "prediction_time": -1 } },
                    { "$limit": 1 }
                ],
                "as": "prediction"
            }
        },
        { "$unwind": { "path": "$prediction", "preserveNullAndEmptyArrays": True } },
        {
            "$project": {
                "_id": 0,
                "id": { "$toString": "$_id" },
                "meter_name": 1,
                "address": "$branch.address",
                "status": { "$ifNull": ["$prediction.predicted_label", "no_prediction"] },
                "prediction_time": "$prediction.prediction_time"
            }
        }
    ]
    
    result = list(db[COL].aggregate(pipeline))
    for doc in result:
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                doc[k] = str(v)
    return result


def remove_meter(mid: str):
    company_id, branch_id, role_id, role_name = get_user_scope()
    cur = get(mid)

    if not cur:
        return False
    
    if branch_id and cur["branch_id"] != oid_str(branch_id):
        return False
    
    if company_id and not branch_id:
        if cur["branch_id"] not in _branch_ids_in_company(company_id):
            return False
        
    db = get_db()
    meter_oid = to_object_id(mid)

    try:
        res = db[COL].delete_one({"_id": meter_oid})
        if res.deleted_count != 1:
            return False

        related_cols = [
            "predictions",
            "meter_manual_thresholds",
            "meter_consumptions",
            "meter_repairs",
            "meter_measurements",
            "alerts",
            "user_meter",
        ]
        for col in related_cols:
            try:
                db[col].delete_many({"meter_id": meter_oid})
            except Exception:
                pass

        return True
    
    except Exception:
        return False


# =====================================
# PREDICTION STATUS CALCULATION UTILS
# =====================================

def _convert_confidence_to_score(confidence, predicted_label):
    if predicted_label == "normal":
        return 0
    elif predicted_label == "leak":
        if confidence == "NNthap":
            return 1
        elif confidence == "NNTB":
            return 2
        elif confidence == "NNcao":
            return 3    
    return 0

def _convert_score_to_status_confidence(score):
    if score == 0:
        return "normal", "normal"
    elif score == 1:
        return "anomaly", "NNthap"
    elif score == 2:
        return "anomaly", "NNTB"
    elif score >= 3:
        return "anomaly", "NNcao"
    else:
        return "unknown", "unknown"

def calculate_meter_status_and_confidence(db, meter_id):
    try:
        lstm_model = db.ai_models.find_one({"name": "lstm"})
        lstm_ae_model = db.ai_models.find_one({"name": "lstm_autoencoder"})
        
        if not lstm_model and not lstm_ae_model:
            return "unknown", "unknown"
            
        current_time = get_vietnam_now()
        start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        predictions_query = {
            "meter_id": meter_id,
            "prediction_time": {"$gte": start_of_day, "$lte": current_time}
        }
        
        all_predictions = list(db.predictions.find(predictions_query).sort("prediction_time", -1))
        
        if not all_predictions:
            return "unknown", "unknown"
        
        lstm_predictions = []
        lstm_ae_predictions = []
        
        for pred in all_predictions:
            model_id = pred.get("model_id")
            if model_id:
                if lstm_model and model_id == lstm_model["_id"]:
                    lstm_predictions.append(pred)
                elif lstm_ae_model and model_id == lstm_ae_model["_id"]:
                    lstm_ae_predictions.append(pred)
        
        lstm_ae_score = 0
        if lstm_ae_predictions:
            scores = []
            for pred in lstm_ae_predictions:
                label = pred.get("predicted_label", "normal")
                confidence = pred.get("confidence", "normal")
                score = _convert_confidence_to_score(confidence, label)
                scores.append(score)
            
            if scores:
                lstm_ae_score = sum(scores) / len(scores)
                lstm_ae_score = int(lstm_ae_score) 
        
        lstm_score = 0
        if lstm_predictions:
            latest_lstm = lstm_predictions[0]
            label = latest_lstm.get("predicted_label", "normal")
            confidence = latest_lstm.get("confidence", "normal")
            lstm_score = _convert_confidence_to_score(confidence, label)
        
        if lstm_predictions and lstm_ae_predictions:
            final_score = (lstm_score + lstm_ae_score) / 2
            final_score = int(final_score) 
        elif lstm_ae_predictions:
            final_score = lstm_ae_score
        elif lstm_predictions:
            final_score = lstm_score
        else:
            return "unknown", "unknown"
        
        return _convert_score_to_status_confidence(final_score)
                
    except Exception as e:
        print(f"Error calculating meter status: {e}")
        return "unknown", "unknown"


def calculate_bulk_meter_status_and_confidence(db, meter_ids):
    if not meter_ids:
        return {}
    
    try:
        lstm_model = db.ai_models.find_one({"name": "lstm"})
        lstm_ae_model = db.ai_models.find_one({"name": "lstm_autoencoder"})
        
        if not lstm_model and not lstm_ae_model:
            return {meter_id: ("unknown", "unknown") for meter_id in meter_ids}
        
        current_time = get_vietnam_now()
        start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_predictions = list(db.predictions.aggregate([
            {
                "$match": {
                    "meter_id": {"$in": meter_ids},
                    "prediction_time": {"$gte": start_of_day, "$lte": current_time}
                }
            },
            {"$sort": {"meter_id": 1, "prediction_time": -1}},
            {
                "$group": {
                    "_id": "$meter_id",
                    "predictions": {"$push": "$$ROOT"}
                }
            }
        ]))
        
        results = {}
        
        for group in all_predictions:
            meter_id = group["_id"]
            predictions = group["predictions"]
            
            if not predictions:
                results[meter_id] = ("unknown", "unknown")
                continue
            
            lstm_predictions = []
            lstm_ae_predictions = []
            
            for pred in predictions:
                model_id = pred.get("model_id")
                if model_id:
                    if lstm_model and model_id == lstm_model["_id"]:
                        lstm_predictions.append(pred)
                    elif lstm_ae_model and model_id == lstm_ae_model["_id"]:
                        lstm_ae_predictions.append(pred)
            
            lstm_ae_score = 0
            if lstm_ae_predictions:
                scores = []
                for pred in lstm_ae_predictions:
                    label = pred.get("predicted_label", "normal")
                    confidence = pred.get("confidence", "normal")
                    score = _convert_confidence_to_score(confidence, label)
                    scores.append(score)
                
                if scores:
                    lstm_ae_score = sum(scores) / len(scores)
                    lstm_ae_score = int(lstm_ae_score)  # Làm tròn xuống
            
            lstm_score = 0
            if lstm_predictions:
                latest_lstm = lstm_predictions[0]
                label = latest_lstm.get("predicted_label", "normal")
                confidence = latest_lstm.get("confidence", "normal")
                lstm_score = _convert_confidence_to_score(confidence, label)
            
            if lstm_predictions and lstm_ae_predictions:
                final_score = (lstm_score + lstm_ae_score) / 2
                final_score = int(final_score)
            elif lstm_ae_predictions:
                final_score = lstm_ae_score
            elif lstm_predictions:
                final_score = lstm_score
            else:
                results[meter_id] = ("unknown", "unknown")
                continue
            
            status, confidence = _convert_score_to_status_confidence(final_score)
            results[meter_id] = (status, confidence)
        
        for meter_id in meter_ids:
            if meter_id not in results:
                results[meter_id] = ("unknown", "unknown")
                
        return results
        
    except Exception as e:
        print(f"Error calculating bulk meter status: {e}")
        return {meter_id: ("unknown", "unknown") for meter_id in meter_ids}


def get_detailed_prediction_with_status(db, meter_id):
    try:
        latest_predictions = list(db.predictions.find(
            {"meter_id": meter_id}, 
            sort=[("prediction_time", -1)]
        ).limit(10))
        
        if not latest_predictions:
            return None, "unknown"
        
        latest_time = latest_predictions[0]["prediction_time"]
        same_time_predictions = [
            p for p in latest_predictions 
            if p["prediction_time"] == latest_time
        ]
        
        normal_preds = [p for p in same_time_predictions if p.get("predicted_label") == "normal"]
        anomaly_preds = [p for p in same_time_predictions if p.get("predicted_label") in ["leak", "anomaly"]]
        
        if len(normal_preds) > 0 and len(anomaly_preds) > 0:
            meter_status = "anomaly"
            best_pred = same_time_predictions[0]
            prediction_dict = _build_prediction_dict(db, best_pred, override_label="anomaly", override_confidence="NNTB")
            
        elif len(anomaly_preds) > 0:
            meter_status = "anomaly"
            best_pred = _find_highest_confidence_prediction(anomaly_preds)
            prediction_dict = _build_prediction_dict(db, best_pred) if best_pred else None
            
        else:
            first_pred = same_time_predictions[0]
            label = first_pred.get("predicted_label", "unknown")
            
            if label == "normal":
                meter_status = "normal"
            elif label == "lost":
                meter_status = "lost"
            else:
                meter_status = "unknown"
                
            prediction_dict = _build_prediction_dict(db, first_pred)
        
        return prediction_dict, meter_status
        
    except Exception as e:
        print(f"Error getting detailed prediction: {e}")
        return None, "unknown"


def get_detailed_predictions_with_status(db, meter_id):
    try:
        latest_predictions = list(db.predictions.find(
            {"meter_id": meter_id}, 
            sort=[("prediction_time", -1)]
        ).limit(10))
        
        if not latest_predictions:
            return [], "unknown"
        
        latest_time = latest_predictions[0]["prediction_time"]
        same_time_predictions = [
            p for p in latest_predictions 
            if p["prediction_time"] == latest_time
        ]
        
        # Xây dựng mảng predictions cho tất cả các model
        predictions_array = []
        for pred in same_time_predictions:
            prediction_dict = _build_prediction_dict(db, pred)
            if prediction_dict:
                predictions_array.append(prediction_dict)
        
        # Tính toán status dựa trên tất cả predictions
        normal_preds = [p for p in same_time_predictions if p.get("predicted_label") == "normal"]
        anomaly_preds = [p for p in same_time_predictions if p.get("predicted_label") in ["leak", "anomaly"]]
        
        if len(normal_preds) > 0 and len(anomaly_preds) > 0:
            meter_status = "anomaly"
        elif len(anomaly_preds) > 0:
            meter_status = "anomaly"
        else:
            first_pred = same_time_predictions[0]
            label = first_pred.get("predicted_label", "unknown")
            
            if label == "normal":
                meter_status = "normal"
            elif label == "lost":
                meter_status = "lost"
            else:
                meter_status = "unknown"
        
        return predictions_array, meter_status
        
    except Exception as e:
        print(f"Error getting detailed predictions: {e}")
        return [], "unknown"


def _find_highest_confidence_prediction(predictions):
    """
    Tìm prediction có confidence cao nhất theo thứ tự ưu tiên:
    Numeric confidence (cao nhất) > "NNcao" > "NNTB" > "NNthap"
    
    Args:
        predictions: List of prediction documents
        
    Returns:
        dict: Prediction document có confidence cao nhất
    """
    # Mapping confidence strings to priority values
    confidence_hierarchy = {
        "NNcao": 3,
        "NNTB": 2, 
        "NNthap": 1
    }
    
    best_pred = None
    best_conf_value = -1
    best_is_numeric = False
    
    for pred in predictions:
        conf_raw = pred.get("confidence")
        if conf_raw is not None:
            try:
                conf_float = float(conf_raw)
                if not best_is_numeric or conf_float > best_conf_value:
                    best_conf_value = conf_float
                    best_pred = pred
                    best_is_numeric = True
            except (ValueError, TypeError):
                conf_str = str(conf_raw).strip()
                conf_priority = confidence_hierarchy.get(conf_str, 0)
                
                if not best_is_numeric:
                    if conf_priority > best_conf_value:
                        best_conf_value = conf_priority
                        best_pred = pred
                elif best_pred is None:
                    best_pred = pred
    
    return best_pred or (predictions[0] if predictions else None)


def _build_prediction_dict(db, prediction_doc, override_label=None, override_confidence=None):
    """
    Xây dựng prediction dictionary từ document
    """
    if not prediction_doc:
        return None
        
    model_doc = db.ai_models.find_one({"_id": prediction_doc["model_id"]})
    model_info = None
    if model_doc:
        model_info = {
            "_id": str(model_doc["_id"]),
            "name": model_doc.get("name"),
        }
    
    return {
        "_id": str(prediction_doc["_id"]),
        "meter_id": str(prediction_doc["meter_id"]),
        "model": model_info,
        "model_name": model_info.get("name") if model_info else None,
        "prediction_time": prediction_doc["prediction_time"],
        "predicted_threshold": prediction_doc.get("predicted_threshold"),
        "predicted_label": override_label or prediction_doc.get("predicted_label"),
        "confidence": override_confidence or prediction_doc.get("confidence"),
        "recorded_instant_flow": prediction_doc.get("recorded_instant_flow"),
    }

# =====================================
# THRESHOLD MANAGEMENT UTILS
# =====================================

def add_threshold_to_meter(meter_id: str, threshold_value: Optional[float] = None, user_id: Optional[str] = None) -> Dict[str, Any]:

    
    
    db = get_db()
    meter_oid = to_object_id(meter_id)
    
    meter = db.meters.find_one({"_id": meter_oid})
    if not meter:
        raise BadRequest("Meter not found")
    
    if threshold_value is None:
        yesterday = get_vietnam_now() - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        yesterday_threshold = get_threshold_by_date(meter_id, yesterday_str)
        
        if yesterday_threshold:
            threshold_value = yesterday_threshold["threshold_value"]
        else:
            latest_threshold = db.meter_manual_thresholds.find_one({
                "meter_id": meter_oid
            }, sort=[("set_time", -1)])
            
            if latest_threshold:
                threshold_value = latest_threshold["threshold_value"]
            else:
                threshold_value = 0.0
    
    today_str = get_vietnam_now().strftime('%Y-%m-%d')
    threshold_doc = {
        "meter_id": meter_oid,
        "threshold_value": float(threshold_value),
        "set_time": today_str,
    }
    
    try:
        today_threshold = get_threshold_by_date(meter_id, today_str)
        if today_threshold:
            result = db.meter_manual_thresholds.update_one(
                {"_id": today_threshold["_id"]},
                {"$set": {"threshold_value": float(threshold_value)}}
            )
        else: 
            result = db.meter_manual_thresholds.insert_one(threshold_doc)

        return {
            "meter_id": meter_id,
            "meter_name": meter["meter_name"],
            "threshold_value": threshold_value,
            "set_time": threshold_doc["set_time"],
        }
        
    except Exception as e:
        raise BadRequest(f"Failed to create threshold: {str(e)}")

def create_daily_thresholds_for_all_meters():
    db = get_db()
    
    try:
        meters = list(db.meters.find({}))
        success_count = 0
        error_count = 0
        
        today = get_vietnam_now()
        today_str = today.strftime('%Y-%m-%d')
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        for meter in meters:
            try:
                meter_id = str(meter["_id"])
                meter_oid = meter["_id"]
                
                existing_threshold = get_threshold_by_date(meter_id, today_str)
                
                if not existing_threshold:
                    yesterday_threshold = get_threshold_by_date(meter_id, yesterday_str)
                    
                    if yesterday_threshold:
                        threshold_value = yesterday_threshold["threshold_value"]
                    else:
                        latest_threshold = db.meter_manual_thresholds.find_one({
                            "meter_id": meter_oid
                        }, sort=[("set_time", -1)])
                        
                        threshold_value = latest_threshold["threshold_value"] if latest_threshold else 0.0
                    
                    threshold_doc = {
                        "meter_id": meter_oid,
                        "threshold_value": float(threshold_value),
                        "set_time": today_str,
                    }
                    
                    db.meter_manual_thresholds.insert_one(threshold_doc)
                    success_count += 1

            except Exception as e:
                error_count += 1
        
        return {"success_count": success_count, "error_count": error_count}
        
    except Exception as e:
        raise

def get_threshold_by_date(meter_id: str, date_str: str):
    """Lấy giá trị ngưỡng cho meter tại ngày cụ thể"""
    try:
        db = get_db()
        
        meter_oid = to_object_id(meter_id)
        
        threshold = db.meter_manual_thresholds.find_one(
            {
                "meter_id": meter_oid,
                "set_time": date_str
            },
            sort=[("set_time", -1)]
        )
        
        return threshold
        
    except Exception as e:
        raise
    