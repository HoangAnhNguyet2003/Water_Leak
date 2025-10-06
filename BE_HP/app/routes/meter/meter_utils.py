# create_meter_admin_only, get_meters_list, list_meters, remove_meter, build_leak_overview
from datetime import datetime, timedelta, timezone
from email import errors
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from bson import ObjectId
from ...models.meter_schema import MeterCreate, MeterOut
from werkzeug.exceptions import BadRequest, Conflict, Forbidden
from ...utils import json_ok, created, parse_pagination, role_name as _role_name, find_branch_by_name, oid_str, get_user_scope, to_object_id
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
        "installation_time": installation_time or datetime.utcnow(),
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
    print("Creating meter with data:", data)
    if _role_name() != "admin":
        raise Forbidden("Only admin can create meter")
    branch = find_branch_by_name(data.branch_name)

    if exists_meter(
        _meter_id_from_name(data.meter_name)
    ):
        print(exists_meter(_meter_id_from_name(data.meter_name)))
        raise Conflict(
            f"Meter '{data.meter_name}' already exists"
        )

    doc = insert_meter(branch["_id"], data.meter_name, data.installation_time)
    doc["branch_name"] = branch["name"]
    return MeterOut(**doc)



def get_meters_list(date_str: str | None = None):
    """
    Lấy danh sách đồng hồ và trạng thái dự đoán trong ngày.
    - Nếu truyền date_str (YYYY-MM-DD) thì lấy đúng ngày đó
    - Nếu không truyền thì mặc định hôm nay (theo giờ VN)
    """ 
    db = get_db()

    # Nếu không truyền thì mặc định hôm nay theo giờ VN
    vn = ZoneInfo("Asia/Ho_Chi_Minh")
    if not date_str:
        date_str = datetime.now(vn).strftime("%Y-%m-%d")

    # Tính khoảng thời gian UTC cho ngày đó
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=vn)
    end_local   = start_local + timedelta(days=1)
    start_utc, end_utc = start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

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
                            "prediction_time": {"$gte": start_utc, "$lt": end_utc}
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

def list_meters(page:int, page_size:int, q: Optional[str], sort: Optional[str]):
    company_id, branch_id, role_id, role_name = get_user_scope()
    if branch_id:
        return list_meter_paginated(page, page_size, [oid_str(branch_id)], q, sort)
    if company_id:
        branches = _branch_ids_in_company(company_id)
        return list_meter_paginated(page, page_size, branches, q, sort)

    return list_meter_paginated(page, page_size, None, q, sort)



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

def calculate_meter_status_and_confidence(db, meter_id):
    """
    Tính toán status và confidence của meter dựa trên multiple model predictions
    
    Args:
        db: Database connection
        meter_id: ObjectId của meter
        
    Returns:
        tuple: (status, confidence)
        
    Logic:
        - Nếu có xung đột (1 normal + 1 anomaly) → status="anomaly", confidence="NNTB"
        - Nếu tất cả anomaly → status="anomaly", confidence=cao nhất
        - Nếu tất cả normal → status="normal", confidence=prediction đầu tiên
        - Các trường hợp khác → giữ nguyên label và confidence
    """
    try:
        latest_predictions = list(db.predictions.find(
            {"meter_id": meter_id}, 
            sort=[("prediction_time", -1)]
        ).limit(10))  
        if not latest_predictions:
            return "unknown", "unknown"
        
        latest_time = latest_predictions[0]["prediction_time"]
        same_time_predictions = [
            p for p in latest_predictions 
            if p["prediction_time"] == latest_time
        ]
        
        normal_predictions = []
        anomaly_predictions = []
        
        for pred in same_time_predictions:
            label = pred.get("predicted_label", "unknown")
            if label == "normal":
                normal_predictions.append(pred)
            elif label in ["leak", "anomaly"]:
                anomaly_predictions.append(pred)
        
        if len(normal_predictions) > 0 and len(anomaly_predictions) > 0:
            # Trường hợp xung đột: có cả normal và anomaly
            return "anomaly", "NNTB"
            
        elif len(anomaly_predictions) > 0:
            best_pred = _find_highest_confidence_prediction(anomaly_predictions)
            confidence = str(best_pred.get("confidence", "unknown")) if best_pred else "unknown"
            return "anomaly", confidence
            
        elif len(normal_predictions) > 0:
            confidence = str(normal_predictions[0].get("confidence", "unknown"))
            return "normal", confidence
            
        else:
            first_pred = same_time_predictions[0]
            label = first_pred.get("predicted_label", "unknown")
            confidence = str(first_pred.get("confidence", "unknown"))
            
            if label == "lost":
                return "lost", confidence
            else:
                return "unknown", confidence
                
    except Exception as e:
        print(f"Error calculating meter status: {e}")
        return "unknown", "unknown"


def get_detailed_prediction_with_status(db, meter_id):
    """
    Lấy thông tin prediction chi tiết với status được tính toán
    
    Args:
        db: Database connection
        meter_id: ObjectId của meter
        
    Returns:
        tuple: (prediction_dict, calculated_status)
    """
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
    """
    Lấy thông tin tất cả predictions chi tiết với status được tính toán
    
    Args:
        db: Database connection
        meter_id: ObjectId của meter
        
    Returns:
        tuple: (predictions_array, calculated_status)
    """
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
    