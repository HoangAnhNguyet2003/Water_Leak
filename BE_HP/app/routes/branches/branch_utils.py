from typing import Any, Dict, List, Optional, Tuple

from ...extensions import get_db
from ...utils import to_object_id, oid_str, parse_pagination, get_user_scope as _get_user_scope

COL = "branches"

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


def list_branches(page:int, page_size:int, q: Optional[str]):
    company_id, branch_id, _, _ = _get_user_scope()
    if branch_id:
        one = get_db()[COL].find_one({"_id": to_object_id(branch_id)})
        if not one:
            one = None

        items = [one] if one else []
        return items, False
    # company scope: lọc theo company_id
    cid_str = oid_str(company_id) if company_id else None
    return list_paginated(page, page_size, cid_str, q)