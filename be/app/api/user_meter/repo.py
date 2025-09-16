from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str

def list_meters_of_user(user_id: str):
    db = get_db()
    cur = db.user_meters.find({"user_id": to_object_id(user_id)})
    out = []
    for link in cur:
        # ghép thêm thông tin meter nếu cần
        m = db.meters.find_one({"_id": link["meter_id"]})
        if m:
            m["id"] = oid_str(m.pop("_id"))
            out.append(m)
    return out

def list_meters_of_user_simple(user_id: str, limit: int = None):
    """Lấy danh sách đơn giản các đồng hồ (chỉ id và tên) với optional limit"""
    db = get_db()
    query = {"user_id": to_object_id(user_id)}

    if limit:
        cur = db.user_meters.find(query).limit(limit)
    else:
        cur = db.user_meters.find(query)

    out = []
    for link in cur:
        m = db.meters.find_one({"_id": link["meter_id"]}, {"_id": 1, "meter_name": 1})
        if m:
            out.append({
                "id": oid_str(m["_id"]),
                "meter_name": m.get("meter_name", "")
            })
    return out
