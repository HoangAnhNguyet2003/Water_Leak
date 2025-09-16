from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str

def get_user_by_username(username: str):
    db = get_db()
    u = db.users.find_one({"username": username})
    if not u: return None
    u["id"] = oid_str(u.pop("_id"))
    return u



def insert_user(doc: dict) -> str:
    db = get_db()
    res = db.users.insert_one(doc)
    return oid_str(res.inserted_id)

def get_user_by_id(uid: str):
    db = get_db()
    u = db.users.find_one({"_id": to_object_id(uid)})
    if not u: return None
    u["id"] = oid_str(u.pop("_id"))
    return u

def get_role(rid: str):
    db = get_db()
    r = db.roles.find_one({"_id": to_object_id(rid)})
    if not r: return None
    r["id"] = oid_str(r.pop("_id"))
    return r