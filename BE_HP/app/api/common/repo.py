from datetime import datetime, timezone
from typing import Dict, Optional, Set
from bson import ObjectId
from ...extensions import get_db

def _pick_log_collection() -> str:
    db = get_db()
    names = set(db.list_collection_names())
    if "log" in names: return "log"
    if "meter_logs" in names: return "meter_logs"
    return "logs"

def _branch_ids_in_company(company_id: ObjectId) -> Set[ObjectId]:
    db = get_db()
    return {b["_id"] for b in db.branches.find({"company_id": company_id}, {"_id": 1})}

def count_meters(company_id: Optional[str] = None) -> int:
    db = get_db()
    if not company_id:
        return db.meters.count_documents({})
    bid_set = _branch_ids_in_company(ObjectId(company_id))
    if not bid_set: return 0
    return db.meters.count_documents({"branch_id": {"$in": list(bid_set)}})

def count_users(company_id: Optional[str] = None) -> int:
    db = get_db()
    if not company_id:
        return db.users.count_documents({})
    # người dùng thuộc công ty (company_id) HOẶC thuộc chi nhánh nằm trong công ty đó
    bid_set = _branch_ids_in_company(ObjectId(company_id))
    query = {"$or": [{"company_id": ObjectId(company_id)}]}
    if bid_set:
        query["$or"].append({"branch_id": {"$in": list(bid_set)}})
    return db.users.count_documents(query)

def count_logs(company_id: Optional[str] = None) -> int:
    db = get_db()
    col = db[_pick_log_collection()]
    if not company_id:
        try:
            return col.count_documents({})
        except Exception:
            return 0

    # ưu tiên field company_id nếu log có
    q = {"company_id": ObjectId(company_id)}
    try:
        has_company_id = col.count_documents(q) > 0
    except Exception:
        has_company_id = False

    if has_company_id:
        return col.count_documents(q)

    # fallback: lọc theo branch_id ∈ branches of company
    bid_set = _branch_ids_in_company(ObjectId(company_id))
    if not bid_set: return 0
    try:
        return col.count_documents({"branch_id": {"$in": list(bid_set)}})
    except Exception:
        return 0

def overview_counts(company_id: Optional[str] = None) -> Dict[str, int]:
    return {
        "total_meters": count_meters(company_id),
        "total_logs":   count_logs(company_id),
        "total_users":  count_users(company_id),
        "updated_at":   datetime.now(timezone.utc).isoformat()
    }
