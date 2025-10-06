from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required,get_jwt_identity
from ...extensions import get_db
from ...require import require_role
from ...models.meter_schema import MeterCreate, MeterOut
from .meter_utils import create_meter_admin_only, get_meters_list, list_meters, remove_meter
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
    print("Creating meter...")
    try:
        current_user = get_jwt()
        print("Current user claims:", current_user)
        data = MeterCreate(**(request.get_json(silent=True) or {}))
        print("Parsed data:", data)
    except Exception as e:
        traceback.print_exc()
        raise BadRequest(f"Invalid request: {e}")
    m = create_meter_admin_only(data)
    return created(f"/api/v1/meters/create/{m.id}", m.model_dump())


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
    out = []
    for x in items:
        branch_name = None
        if x.get("branch_id") and x["branch_id"]:
            try:
                branch = db["branches"].find_one({"_id": ObjectId(x["branch_id"])})
                branch_name = branch.get("name") if branch else None
            except:
                branch_name = None

        meter_out = MeterOut(**x).model_dump(mode="json")
        meter_out["branchName"] = branch_name
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
    """
    - Lấy toàn bộ danh sách đồng hồ và trạng thái dự đoán trong ngày, dùng cho dashboard và mục đồng hồ của tổng công ty
    - Ví dụ mẫu trả về:
    {
        "id": "66a1b2c3d4e5f67890123456",
        "meter_name": "Meter A",
        "address": "ABCD",
        "status": "anomaly",
        "prediction_time": "2025-04-05T08:22:15Z"
    }
    """
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

    out = []
    for x in meters:
        branch_name = None
        if x.get("branch_id"):
            branch = db["branches"].find_one({"_id": x["branch_id"]})
            branch_name = branch.get("name") if branch else None

        meter_id_str = str(x["_id"])

        # Lấy threshold mới nhất
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

        # Lấy measurement mới nhất
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

        # Lấy thông tin sửa chữa mới nhất
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

        # 🔹 Lấy prediction mới nhất cho đồng hồ này
        prediction_doc = db.predictions.find_one(
            {"meter_id": x["_id"]}, sort=[("prediction_time", -1)]
        )
        prediction = None
        if prediction_doc:
            # Lấy model tương ứng
            model_doc = db.ai_models.find_one({"_id": prediction_doc["model_id"]})
            model_info = None
            if model_doc:
                model_info = {
                    "_id": str(model_doc["_id"]),
                    "name": model_doc.get("name"),
                }

            prediction = {
                "_id": str(prediction_doc["_id"]),
                "meter_id": str(prediction_doc["meter_id"]),
                "model": model_info,
                "model_name": model_info.get("name") if model_info else None,
                "prediction_time": prediction_doc["prediction_time"],
                "predicted_threshold": prediction_doc.get("predicted_threshold"),
                "predicted_label": prediction_doc.get("predicted_label"),
                "confidence": prediction_doc.get("confidence"),
                "recorded_instant_flow": prediction_doc.get("recorded_instant_flow"),
            }

        # Tạo meter_out object (di chuyển ra ngoài if prediction_doc)
        meter_out = {
            "_id": meter_id_str,
            "branch_id": str(x["branch_id"]),
            "meter_name": x["meter_name"],
            "installation_time": x.get("installation_time"),
            "branchName": branch_name,
            "threshold": threshold,
            "measurement": measurement,
            "repair": repair,
            "prediction": prediction,  # có thể là None nếu không có prediction
        }

        out.append(meter_out)

    return json_ok({"items": out})
