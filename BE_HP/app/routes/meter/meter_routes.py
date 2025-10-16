from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required,get_jwt_identity
from ...extensions import get_db
from ...require import require_role
from ...models.meter_schema import MeterCreate, MeterOut
from .meter_utils import create_meter_admin_only, get_meters_list, list_meters, remove_meter, calculate_meter_status_and_confidence, calculate_bulk_meter_status_and_confidence, get_detailed_prediction_with_status, get_detailed_predictions_with_status, add_threshold_to_meter
from ...error import BadRequest
from ...utils import json_ok, created, parse_pagination, get_swagger_path
import traceback
from flasgger import swag_from


meter_bp = Blueprint("meters", __name__)


@meter_bp.post("/create")
@swag_from(get_swagger_path('meter/create.yml'))
@jwt_required()
@require_role("admin")
def create():
    try:
        current_user = get_jwt()
        data = MeterCreate(**(request.get_json(silent=True) or {}))
    except Exception as e:
        traceback.print_exc()
        raise BadRequest(f"Invalid request: {e}")
    m = create_meter_admin_only(data)
    return created(f"/api/v1/meters/create/{m.id}", m.model_dump())

@meter_bp.post("/add_new_threshold/<string:mid>")
@jwt_required()
@require_role("branch_manager", "company_manager", "admin") 
def add_new_threshold(mid):
    """Thêm threshold mới cho meter"""
    try: 
        current_user = get_jwt()
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        threshold_value = data.get("threshold_value")  # Có thể là None
        
        result = add_threshold_to_meter(mid, threshold_value, user_id)
        
        return jsonify({
            "success": True,
            "message": "Threshold đã được thêm thành công",
            "data": result
        }), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@meter_bp.get("/threshold/<string:mid>/<string:date>")
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def get_threshold_by_date(mid, date):
    """Lấy giá trị ngưỡng cho meter tại ngày cụ thể"""
    try:
        from .meter_utils import get_threshold_by_date
        
        threshold = get_threshold_by_date(mid, date)
        
        if threshold:
            return jsonify({
                "success": True,
                "threshold_value": threshold["threshold_value"],
                "set_time": threshold["set_time"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Không tìm thấy ngưỡng cho ngày này"
            }), 404
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
@meter_bp.get("/get_all_meters")
@swag_from(get_swagger_path('meter/get_all_meters.yml'))
@jwt_required()
@require_role("admin", "company_manager")
def list_():
    page, page_size = parse_pagination(request.args)
    q = request.args.get("q")
    sort = request.args.get("sort")

    items, has_next = list_meters(page, page_size, q, sort)

    db = get_db()
    
    # Tối ưu hóa: Tính toán bulk status cho tất cả meters
    meter_ids = [ObjectId(x.get("_id") or x.get("id")) for x in items if x.get("_id") or x.get("id")]
    status_results = calculate_bulk_meter_status_and_confidence(db, meter_ids) if meter_ids else {}
    
    out = []
    for x in items:
        branch_name = None
        if x.get("branch_id") and x["branch_id"]:
            try:
                branch = db["branches"].find_one({"_id": ObjectId(x["branch_id"])})
                branch_name = branch.get("name") if branch else None
            except:
                branch_name = None

        # Lấy status và confidence từ kết quả bulk calculation
        meter_id = x.get("_id") or x.get("id")
        if meter_id and ObjectId(meter_id) in status_results:
            status, confidence = status_results[ObjectId(meter_id)]
        else:
            status, confidence = "unknown", "unknown"
        
        meter_out = MeterOut(**x).model_dump(mode="json")
        meter_out["branchName"] = branch_name
        meter_out["status"] = status  
        meter_out["confidence"] = confidence  
                
        out.append(meter_out)

    body = {"items": out, "page": page, "page_size": page_size}

    return json_ok(body)

@meter_bp.delete("delete/<string:mid>")
@swag_from(get_swagger_path('meter/delete.yml'))
@jwt_required()
@require_role("admin")
def remove(mid):
    ok = remove_meter(mid)
    if ok:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Not found"}}), 404

@meter_bp.get("/get_all_with_status")
@swag_from(get_swagger_path('meter/get_all_with_status.yml'))
@jwt_required()
@require_role(["company_manager"])
def list_meters_with_status():
    date_str = request.args.get("date")  
    items = get_meters_list(date_str)
    return jsonify({"items": items}), 200

@meter_bp.get("/get_my_meters")
@swag_from(get_swagger_path('meter/get_my_meters.yml'))
@jwt_required()
@require_role("branch_manager")
def get_my_meters():
    db = get_db()
    user_id = get_jwt_identity()
    user_meter_docs = db.user_meter.find({"user_id": ObjectId(user_id)})
    meter_ids = [doc["meter_id"] for doc in user_meter_docs]
    meters = list(db.meters.find({"_id": {"$in": meter_ids}}))

    # Tối ưu hóa: Tính toán bulk status cho tất cả meters
    meter_object_ids = [x["_id"] for x in meters]
    status_results = calculate_bulk_meter_status_and_confidence(db, meter_object_ids) if meter_object_ids else {}
    
    out = []
    for x in meters:
        branch_name = None
        if x.get("branch_id"):
            branch = db["branches"].find_one({"_id": x["branch_id"]})
            branch_name = branch.get("name") if branch else None

        meter_id_str = str(x["_id"])

        threshold_doc = db.meter_manual_thresholds.find_one(
            {"meter_id": x["_id"]}, sort=[("set_time", -1)]
        )
        threshold = None
        if threshold_doc:
            threshold = {
                "id": str(threshold_doc["_id"]),
                "meter_id": str(threshold_doc["meter_id"]),
                "set_time": threshold_doc["set_time"],
                "threshold_value": threshold_doc["threshold_value"],
            }

        measurement_doc = db.meter_measurements.find_one(
            {"meter_id": x["_id"]}, sort=[("measurement_time", -1)]
        )
        measurement = None
        if measurement_doc:
            measurement = {
                "id": str(measurement_doc["_id"]),
                "meter_id": str(measurement_doc["meter_id"]),
                "measurement_time": measurement_doc["measurement_time"],
                "instant_flow": measurement_doc["instant_flow"],
                "instant_pressure": measurement_doc["instant_pressure"],
            }

        repair_doc = db.meter_repairs.find_one(
            {"meter_id": x["_id"]}, sort=[("repair_time", -1)]
        )
        repair = None
        if repair_doc:
            repair = {
                "_id": str(repair_doc["_id"]),
                "meter_id": str(repair_doc["meter_id"]),
                "recorded_time": repair_doc.get("recorded_time"),
                "repair_time": repair_doc.get("repair_time"),
                "leak_reason": repair_doc.get("leak_reason"),
            }

        # Lấy status từ bulk calculation thay vì tính toán riêng lẻ
        if x["_id"] in status_results:
            meter_status, meter_confidence = status_results[x["_id"]]
        else:
            meter_status, meter_confidence = "unknown", "unknown"
            
        predictions, _ = get_detailed_predictions_with_status(db, x["_id"])
        prediction, _ = get_detailed_prediction_with_status(db, x["_id"])

        meter_out = {
            "_id": meter_id_str,
            "branch_id": str(x["branch_id"]),
            "meter_name": x["meter_name"],
            "installation_time": x.get("installation_time"),
            "branchName": branch_name,
            "status": meter_status,  # Sử dụng status từ bulk calculation
            "confidence": meter_confidence,  # Thêm confidence
            "threshold": threshold,
            "measurement": measurement,
            "repair": repair,
            "prediction": prediction,  # Giữ lại prediction cũ
            "predictions": predictions,  # Trả về mảng predictions mới
        }

        out.append(meter_out)

    return json_ok({"items": out})
