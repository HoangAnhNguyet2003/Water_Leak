from bson import ObjectId
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ...extensions import get_db
from ...require import require_role
from ...error import BadRequest
from ...utils import json_ok, parse_pagination, get_swagger_path
from flasgger import swag_from
import traceback

from ...models.repair_schema import RepairOut  

repair_bp = Blueprint("repairs", __name__)

@repair_bp.get("/get_all_repairs")
@swag_from(get_swagger_path('meter/get_all_repairs.yml'))
@jwt_required()
@require_role("company_manager")
def list_repairs():
    try:
        page, page_size = parse_pagination(request.args)
        q = request.args.get("q")
        sort = request.args.get("sort")

        db = get_db()
        query = {}
        if q:
            query["$or"] = [
                {"leak_reason": {"$regex": q, "$options": "i"}},
                {"replacement_location": {"$regex": q, "$options": "i"}},
                {"replacement_type": {"$regex": q, "$options": "i"}},
            ]

        cursor = db["meter_repairs"].find(query)

        if sort:
            sort_key = sort.lstrip("-")
            direction = -1 if sort.startswith("-") else 1
            cursor = cursor.sort(sort_key, direction)

        # Pagination
        items = list(cursor.skip((page - 1) * page_size).limit(page_size + 1))
        has_next = len(items) > page_size
        items = items[:page_size]

        out = []
        for x in items:
            raw_meter_id = x.get("meter_id")  # lấy giá trị gốc
            meter_id = str(raw_meter_id) if raw_meter_id else None
            
            meter_name = None
            raw_meter_id = x.get("meter_id")
            meter_id = str(raw_meter_id) if raw_meter_id else None

            meter_name = None
            if raw_meter_id:
                try:
                    meter = db["meters"].find_one({"_id": ObjectId(raw_meter_id)})
                    meter_name = meter.get("meter_name") if meter else None
                except Exception as e:
                    print("DEBUG convert meter_id failed:", raw_meter_id, e)



            repair_out = RepairOut(
                id=str(x.get("_id")),
                meterId=meter_id,
                meterName=meter_name,
                recordedTime=x.get("recorded_time"),
                repairTime=x.get("repair_time"),
                leakReason=x.get("leak_reason"),
                leakFix=x.get("leak_fix"),
                replacementLocation=x.get("replacement_location"),
                replacementType=x.get("replacement_type"),
            ).model_dump(mode="json")

            out.append(repair_out)


        body = {"items": out, "page": page, "page_size": page_size, "has_next": has_next}
        return json_ok(body)

    except Exception as e:
        traceback.print_exc()
        raise BadRequest(f"Invalid request: {e}")
