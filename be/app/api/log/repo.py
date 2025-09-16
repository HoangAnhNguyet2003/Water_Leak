from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from ...extensions import get_db

COL = "log"  # đổi nếu bạn đặt tên khác

def _to_oid(v): return v if isinstance(v, ObjectId) else ObjectId(v)

def _sid(v): return str(v) if v is not None else None

def _doc_to_api(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Giữ nguyên tất cả field; chỉ convert ObjectId → str, datetime → iso."""
    out: Dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    return out

def _branch_ids_in_company(company_id: ObjectId) -> List[ObjectId]:
    db = get_db()
    return [b["_id"] for b in db.branches.find({"company_id": company_id}, {"_id": 1})]

def _user_ids_in_company(company_id: ObjectId) -> List[ObjectId]:
    """Tập user thuộc công ty: user.company_id == company_id hoặc user.branch_id ∈ branches của công ty."""
    db = get_db()
    bids = _branch_ids_in_company(company_id)
    q = {"$or": [{"company_id": company_id}]}
    if bids:
        q["$or"].append({"branch_id": {"$in": bids}})
    return [u["_id"] for u in db.users.find(q, {"_id": 1})]

def build_company_scope_query(company_id: str) -> Dict[str, Any]:
    """Vì log không có company_id/branch_id, lọc theo user_id ∈ users của công ty."""
    uids = _user_ids_in_company(_to_oid(company_id))
    if not uids:
        return {"user_id": {"$in": []}}  # rỗng
    return {"user_id": {"$in": uids}}

def find_log_by_id(log_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    return db[COL].find_one({"_id": _to_oid(log_id)})

def delete_log_by_id(log_id: str) -> bool:
    db = get_db()
    res = db[COL].delete_one({"_id": _to_oid(log_id)})
    return res.deleted_count == 1

def user_ids_in_company(company_id: str) -> List[ObjectId]:
    """Tập user thuộc công ty: user.company_id == company_id hoặc user.branch_id ∈ branches của công ty."""
    db = get_db()
    cid = _to_oid(company_id)
    bids = _branch_ids_in_company(cid)
    q = {"$or": [{"company_id": cid}]}
    if bids:
        q["$or"].append({"branch_id": {"$in": bids}})
    return [u["_id"] for u in db.users.find(q, {"_id": 1})]

def list_logs(query: Dict[str, Any], page=1, limit=20, sort="created_time", order="desc") -> Dict[str, Any]:
    db = get_db()
    col = db[COL]
    page  = max(1, int(page or 1))
    limit = min(200, max(1, int(limit or 20)))
    direction = DESCENDING if (order or "").lower() == "desc" else ASCENDING

    cursor = col.find(query).sort([(sort, direction)]).skip((page-1)*limit).limit(limit)
    items = [_doc_to_api(d) for d in cursor]
    total = col.count_documents(query)

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit
    }

def insert_log(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    doc gồm: user_id(ObjectId), log_type, severity, message, created_time(datetime),
             (optional) company_id(ObjectId), branch_id(ObjectId), meta(dict)
    """
    db = get_db()
    res = db[COL].insert_one(doc)

    # Trả ra bản đã chuẩn hoá
    out = {
        "id": _sid(res.inserted_id),
        "user_id": _sid(doc["user_id"]),
        "log_type": doc["log_type"],
        "severity": doc["severity"],
        "message": doc["message"],
        "created_time": doc["created_time"].isoformat(),
        "meta": doc.get("meta"),
    }
    return out