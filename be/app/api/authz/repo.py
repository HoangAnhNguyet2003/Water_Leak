from ...extensions import get_db
from ...utils.bson import to_object_id

def load_permissions_for_user(user_id: str) -> set[str]:
    db = get_db()
    u = db.users.find_one({"_id": to_object_id(user_id)}, {"role_id": 1})
    if not u or not u.get("role_id"):
        return set()
    role_id = u["role_id"]
    # lấy permission_id từ role_permissions
    rp_cur = db.role_permissions.find({"role_id": role_id}, {"permission_id": 1})
    perm_ids = [doc["permission_id"] for doc in rp_cur]
    # lấy description các permission
    perms = set()
    if perm_ids:
        for p in db.permissions.find({"_id": {"$in": perm_ids}}, {"description": 1, "key": 1, "role_name" :1 }):
            print("Found permission:", p)
            perms.add(p["key"])
    return perms
