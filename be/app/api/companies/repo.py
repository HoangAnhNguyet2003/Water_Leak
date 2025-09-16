from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str

COL = "companies"

def insert(doc): 
    res = get_db()[COL].insert_one(doc)
    return oid_str(res.inserted_id)

def get(cid: str):
    d = get_db()[COL].find_one({"_id": to_object_id(cid)})
    if not d: return None
    d["id"] = oid_str(d.pop("_id"))
    return d

def find_by_name(name: str):
    d = get_db()[COL].find_one({"name": name})
    if not d: return None
    d["id"] = oid_str(d.pop("_id"))
    return d
