from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
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
@require_role("admin")
def list_():
    page, page_size = parse_pagination(request.args)
    q = request.args.get("q")
    sort = request.args.get("sort")

    items, has_next = list_meters(page, page_size, q, sort)

    db = get_db()
    out = []
    for x in items:
        branch_name = None
        if x.get("branch_id"):
            branch = db["branches"].find_one({"_id": ObjectId(x["branch_id"])})
            branch_name = branch.get("name") if branch else None

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