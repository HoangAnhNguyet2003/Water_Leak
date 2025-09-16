from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from ...extensions import get_db
from ..authz.require import require_permissions, require_password_confirmation, require_role
from .schemas import MeterCreate, MeterUpdate, MeterOut
from .service import create_meter_admin_only, get_meter, list_meters, remove_meter
from ...errors import BadRequest
from ..common.response import json_ok, created, no_content
from ..common.pagination import parse_pagination, build_links
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
