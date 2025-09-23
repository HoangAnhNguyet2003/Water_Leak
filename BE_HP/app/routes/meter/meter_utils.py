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
    