from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from ...extensions import get_db
from ..authz.require import require_role
from .schemas import MeterCreate, MeterUpdate, MeterOut
from .service import create_meter_admin_only, get_meter, get_meters_list, list_meters, remove_meter, build_leak_overview
from ...errors import BadRequest
from ..common.response import json_ok, created, no_content
from ..common.pagination import parse_pagination, build_links
from ...utils.time_utils import day_bounds_utc
import traceback


bp = Blueprint("meters", __name__, url_prefix="meters")

@bp.post("/create")
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


@bp.get("/get_all_meters")
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

        meter_out = MeterOut(**x).model_dump()
        meter_out["branchName"] = branch_name
        out.append(meter_out)

    body = {"items": out, "page": page, "page_size": page_size}

    return json_ok(body)

@bp.delete("delete/<string:mid>")
@jwt_required()
@require_role("admin")
def remove(mid):
    ok = remove_meter(mid)
    if ok:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Not found"}}), 404

@bp.get("/get_all_with_status")
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


@bp.get("/get_num_leaks_and_normal_meters")
@jwt_required()
@require_role(["branch_manager", "company_manager"])
def leak_overview():
    """
    Dùng cho dashboard tổng công ty.
    Dạng json trả về của result : {
        "total_meters": 1,
        "leak_meters": 1,
        "normal_meters": 0,
    }
    """
    try:
        date_q = request.args.get("date")
        date_str, start_utc, end_utc = day_bounds_utc(date_q)

        result = build_leak_overview(start_utc, end_utc)
        return jsonify({"success": True, "date": date_str, **result}), 200

    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception:
        return jsonify({"success": False, "error": "Internal server error"}), 500