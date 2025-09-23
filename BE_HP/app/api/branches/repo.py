from typing import Optional, Dict, Any, List, Tuple
from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str

COL = "branches"

def insert(doc: Dict[str, Any]) -> str:
    res = get_db()[COL].insert_one(doc)
    return oid_str(res.inserted_id)

def get(bid: str) -> Optional[Dict[str, Any]]:
    d = get_db()[COL].find_one({"_id": to_object_id(bid)})
    if not d: return None
    return d

def list_paginated(page:int, page_size:int, company_id: Optional[str], q: Optional[str]) -> Tuple[List[Dict[str,Any]], bool]:
    db = get_db()
    flt: Dict[str, Any] = {}
    if company_id:
        flt["company_id"] = to_object_id(company_id)
    if q:
        flt["name"] = {"$regex": q, "$options": "i"}

    skip = (page-1) * page_size
    cur = db[COL].find(flt).sort([("_id",1)]).skip(skip).limit(page_size+1)
    out = []
    for d in cur:
        d["id"] = oid_str(d.pop("_id"))
        d["company_id"] = oid_str(d["company_id"])
        out.append(d)
    has_next = len(out) > page_size
    if has_next: out = out[:page_size]
    return out, has_next

def update(bid: str, patch: Dict[str, Any]) -> bool:
    res = get_db()[COL].update_one({"_id": to_object_id(bid)}, {"$set": patch})
    return res.matched_count == 1

def delete(bid: str) -> bool:
    res = get_db()[COL].delete_one({"_id": to_object_id(bid)})
    return res.deleted_count == 1
