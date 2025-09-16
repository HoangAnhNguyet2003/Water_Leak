import os
from datetime import datetime
import bcrypt as bc
from pymongo import MongoClient, ASCENDING, ReturnDocument
from typing import Optional, Dict, Any, List, Set

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB  = os.getenv("MONGO_DB", "Nuoc_HP")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

def reset_collections():
    print("Resetting collections...")
    for col in ["companies", "branches", "meters", "users", "roles", "permissions", "role_permissions"]:
        db[col].drop()

    # Xóa toàn bộ index mặc định (trừ _id_)
    for col_name in db.list_collection_names():
        indexes = db[col_name].index_information()
        for idx in indexes:
            if idx != "_id_":
                db[col_name].drop_index(idx)

def hash_password(plain: str) -> str:
    return bc.hashpw(plain.encode("utf-8"), bc.gensalt()).decode("utf-8")

def upsert(collection: str, query: Dict[str, Any], doc: Dict[str, Any]):
    return db[collection].find_one_and_update(
        query, {"$setOnInsert": doc}, upsert=True, return_document=ReturnDocument.AFTER
    )

# -----------------------
# PERMISSIONS & ROLES
# -----------------------
def seed_permissions_roles():
    # 1) Permissions
    perms = [
        {"key": "branch:read",   "description": "Xem chi nhánh"},
        {"key": "branch:create", "description": "Tạo chi nhánh"},
        {"key": "branch:update", "description": "Sửa chi nhánh"},
        {"key": "branch:delete", "description": "Xóa chi nhánh"},
        {"key": "meter:read",    "description": "Xem đồng hồ"},
        {"key": "meter:create",  "description": "Tạo đồng hồ"},
        {"key": "meter:update",  "description": "Sửa đồng hồ"},
        {"key": "meter:delete",  "description": "Xóa đồng hồ"},
        {"key": "user:read",     "description": "Xem người dùng"},
        {"key": "user:create",   "description": "Tạo người dùng"},
        {"key": "user:update",   "description": "Sửa người dùng"},
        {"key": "user:delete",   "description": "Xóa người dùng"},
        {"key": "log:read",      "description": "Xem nhật ký hệ thống"},
        {"key": "log:create",    "description": "Tạo nhật ký hệ thống"},
        {"key": "log:delete",    "description": "Xóa nhật ký hệ thống"},
    ]
    for p in perms:
        upsert("permissions", {"key": p["key"]}, p)

    # 2) Roles
    roles = [
        {"role_name": "admin"},
        {"role_name": "company_manager"},
        {"role_name": "branch_manager"},
    ]
    for r in roles:
        upsert("roles", {"role_name": r["role_name"]}, r)

    # 3) Map role -> permissions
    perm_docs = {p["key"]: p for p in db.permissions.find({}, {"_id": 1, "key": 1})}
    role_docs = {r["role_name"]: r for r in db.roles.find({}, {"_id": 1, "role_name": 1})}

    def bind(role_name: str, perm_keys: List[str]):
        missing = [k for k in perm_keys if k not in perm_docs]
        if missing:
            raise KeyError(f"Permission keys not found: {missing}")

        role_id = role_docs[role_name]["_id"]
        db.role_permissions.delete_many({"role_id": role_id})
        rp_docs = [{"role_id": role_id, "perm_key": k, "permission_id": perm_docs[k]["_id"]} for k in perm_keys]
        if rp_docs:
            db.role_permissions.insert_many(rp_docs)

    # admin: tất cả
    bind("admin", list(perm_docs.keys()))

    # company_manager: CHỈ READ
    bind("company_manager", [
        "branch:read",
        "user:read",
        "meter:read",
    ])

    # branch_manager: CHỈ READ
    bind("branch_manager", [
        "user:read",
        "meter:read",
    ])

def seed_org():
    # Company
    comp = upsert("companies", {"name": "Công ty Cấp Nước Hải Phòng"},
                  {"name": "Công ty Cấp Nước Hải Phòng", "address": "Hải Phòng"})
    company_id = comp["_id"]

    # Branches
    branches = [
        {"company_id": company_id, "name": "Văn Đẩu",   "address": "Hải Phòng - Văn Đẩu"},
        {"company_id": company_id, "name": "Bắc Sơn",   "address": "Hải Phòng - Bắc Sơn"},
        {"company_id": company_id, "name": "Trường Sơn","address": "Hải Phòng - Trường Sơn"},
    ]
    ids = {}
    for b in branches:
        doc = upsert("branches", {"company_id": b["company_id"], "name": b["name"]}, b)
        ids[b["name"]] = doc["_id"]

    # Meters
    meters = [
        {"branch_id": ids["Văn Đẩu"],    "meter_name": "Đồng hồ Văn Đẩu 01", "installation_time": datetime(2023,5,10,8,0,0)},
        {"branch_id": ids["Văn Đẩu"],    "meter_name": "Đồng hồ Văn Đẩu 02", "installation_time": datetime(2023,6,12,8,0,0)},
        {"branch_id": ids["Văn Đẩu"],    "meter_name": "Đồng hồ Văn Đẩu 03", "installation_time": datetime(2023,7,18,8,0,0)},
        {"branch_id": ids["Văn Đẩu"],    "meter_name": "Đồng hồ Văn Đẩu 04", "installation_time": datetime(2023,8,22,8,0,0)},
        {"branch_id": ids["Văn Đẩu"],    "meter_name": "Đồng hồ Văn Đẩu 05", "installation_time": datetime(2023,9,5,8,0,0)},
        {"branch_id": ids["Bắc Sơn"],    "meter_name": "Đồng hồ Bắc Sơn 01", "installation_time": datetime(2023,7,15,8,0,0)},
        {"branch_id": ids["Bắc Sơn"],    "meter_name": "Đồng hồ Bắc Sơn 02", "installation_time": datetime(2023,8,10,8,0,0)},
        {"branch_id": ids["Bắc Sơn"],    "meter_name": "Đồng hồ Bắc Sơn 03", "installation_time": datetime(2023,9,12,8,0,0)},
        {"branch_id": ids["Bắc Sơn"],    "meter_name": "Đồng hồ Bắc Sơn 04", "installation_time": datetime(2023,10,8,8,0,0)},
        {"branch_id": ids["Trường Sơn"], "meter_name": "Đồng hồ Trường Sơn 01", "installation_time": datetime(2023,8,20,8,0,0)},
        {"branch_id": ids["Trường Sơn"], "meter_name": "Đồng hồ Trường Sơn 02", "installation_time": datetime(2023,9,25,8,0,0)},
        {"branch_id": ids["Trường Sơn"], "meter_name": "Đồng hồ Trường Sơn 03", "installation_time": datetime(2023,10,15,8,0,0)},
    ]
    for m in meters:
        upsert("meters", {"branch_id": m["branch_id"], "meter_name": m["meter_name"]}, m)

    return company_id, ids

def seed_users(company_id, branch_ids: Dict[str, Any]):
    role = {r["role_name"]: r["_id"] for r in db.roles.find({}, {"role_name": 1})}

    users = [
        {"username": "admin",          "password": hash_password("Admin@123"),   "role_id": role["admin"],            "branch_id": None},
        {"username": "tongcongty",     "password": hash_password("Company@123"), "role_id": role["company_manager"],  "company_id": company_id, "branch_id": None},
        {"username": "van_dau_mgr",    "password": hash_password("Branch@123"),  "role_id": role["branch_manager"],   "branch_id": branch_ids["Văn Đẩu"]},
        {"username": "bac_son_mgr",    "password": hash_password("Branch@123"),  "role_id": role["branch_manager"],   "branch_id": branch_ids["Bắc Sơn"]},
        {"username": "truong_son_mgr", "password": hash_password("Branch@123"),  "role_id": role["branch_manager"],   "branch_id": branch_ids["Trường Sơn"]},
        # Thêm nhiều users hơn
        {"username": "user_vd1",       "password": hash_password("User@123"),    "role_id": role["branch_manager"],   "branch_id": branch_ids["Văn Đẩu"]},
        {"username": "user_vd2",       "password": hash_password("User@123"),    "role_id": role["branch_manager"],   "branch_id": branch_ids["Văn Đẩu"]},
        {"username": "user_bs1",       "password": hash_password("User@123"),    "role_id": role["branch_manager"],   "branch_id": branch_ids["Bắc Sơn"]},
        {"username": "user_bs2",       "password": hash_password("User@123"),    "role_id": role["branch_manager"],   "branch_id": branch_ids["Bắc Sơn"]},
        {"username": "user_ts1",       "password": hash_password("User@123"),    "role_id": role["branch_manager"],   "branch_id": branch_ids["Trường Sơn"]},
        {"username": "user_ts2",       "password": hash_password("User@123"),    "role_id": role["branch_manager"],   "branch_id": branch_ids["Trường Sơn"]},
        {"username": "company_mgr2",   "password": hash_password("Company@123"), "role_id": role["company_manager"],  "company_id": company_id, "branch_id": None},
    ]
    for u in users:
        upsert("users", {"username": u["username"]}, {**u, "is_active": True, "last_login": None})

def seed_user_meter(company_id, branch_ids: Dict[str, Any]):
   

    users = list(db.users.find({}, {"_id": 1, "username": 1, "role_id": 1, "branch_id": 1}))
    meters = list(db.meters.find({}, {"_id": 1, "branch_id": 1}))
    roles = {r["_id"]: r["role_name"] for r in db.roles.find({}, {"_id": 1, "role_name": 1})}

    db.user_meter.delete_many({})

    user_meter_docs = []

    for user in users:
        role_name = roles.get(user["role_id"])
        if role_name == "admin":
            continue
        elif role_name == "company_manager":
            for meter in meters:
                user_meter_docs.append({
                    "user_id": user["_id"],
                    "meter_id": meter["_id"],
                })
        elif role_name == "branch_manager":
            user_branch_id = user.get("branch_id")
            if user_branch_id:
                for meter in meters:
                    if meter["branch_id"] == user_branch_id:
                        user_meter_docs.append({
                            "user_id": user["_id"],
                            "meter_id": meter["_id"],
                        })

    if user_meter_docs:
        db.user_meter.insert_many(user_meter_docs)
        print(f"Đã tạo {len(user_meter_docs)} quan hệ user-meter")
    else:
        print("Không có quan hệ user-meter nào được tạo")

# --- Authorization helpers ---
def role_permissions(role_id) -> Set[str]:
    perms = db.role_permissions.find({"role_id": role_id}, {"perm_key": 1, "_id": 0})
    return {p["perm_key"] for p in perms}

def can(user: Dict[str, Any], perm_key: str) -> bool:
    rperms = role_permissions(user["role_id"])
    return perm_key in rperms

# --- READ APIs (demo) ---
def list_branches(actor_username: str) -> List[Dict[str, Any]]:
    user = db.users.find_one({"username": actor_username})
    if not user or not can(user, "branch:read"):
        raise PermissionError("Bạn không có quyền xem chi nhánh")
    # Demo: cho xem tất cả (tùy bạn áp scope nếu muốn)
    return list(db.branches.find({}, {"_id": 0, "name": 1, "address": 1}))

def list_meters(actor_username: str) -> List[Dict[str, Any]]:
    user = db.users.find_one({"username": actor_username})
    if not user or not can(user, "meter:read"):
        raise PermissionError("Bạn không có quyền xem đồng hồ")
    # Demo: cho xem tất cả (tùy bạn áp scope nếu muốn)
    cur = db.meters.find({}, {"_id": 0, "branch_id": 1, "meter_name": 1, "installation_time": 1})
    return list(cur)

# --- WRITE APIs (admin only via permission) ---
def create_branch(actor_username: str, company_id, name: str, address: str):
    user = db.users.find_one({"username": actor_username})
    if not user or not can(user, "branch:create"):
        raise PermissionError("Bạn không có quyền tạo chi nhánh")
    # (Có thể thêm scope cho admin nếu cần, hiện tại chỉ admin có perm này)
    doc = {"company_id": company_id, "name": name, "address": address}
    upsert("branches", {"company_id": company_id, "name": name}, doc)
    return True

def create_meter(actor_username: str, branch_id, meter_name: str, installation_time: Optional[datetime] = None):
    user = db.users.find_one({"username": actor_username})
    if not user or not can(user, "meter:create"):
        raise PermissionError("Bạn không có quyền tạo đồng hồ")
    doc = {
        "branch_id": branch_id,
        "meter_name": meter_name,
        "installation_time": installation_time or datetime.utcnow()
    }
    upsert("meters", {"branch_id": branch_id, "meter_name": meter_name}, doc)
    return True

def update_meter(actor_username: str, branch_id, meter_name: str, new_name: Optional[str] = None):
    user = db.users.find_one({"username": actor_username})
    if not user or not can(user, "meter:update"):
        raise PermissionError("Bạn không có quyền sửa đồng hồ")
    if not new_name:
        raise ValueError("new_name is required")
    res = db.meters.update_one(
        {"branch_id": branch_id, "meter_name": meter_name},
        {"$set": {"meter_name": new_name}}
    )
    return res.modified_count > 0

def delete_meter(actor_username: str, branch_id, meter_name: str):
    user = db.users.find_one({"username": actor_username})
    if not user or not can(user, "meter:delete"):
        raise PermissionError("Bạn không có quyền xóa đồng hồ")
    res = db.meters.delete_one({"branch_id": branch_id, "meter_name": meter_name})
    return res.deleted_count > 0

def main():
    print(f"Connecting to {MONGO_URI}, DB={MONGO_DB}")
    reset_collections()
    seed_permissions_roles()
    company_id, branch_ids = seed_org()
    seed_users(company_id, branch_ids)
    seed_user_meter(company_id, branch_ids)

    print("\n[READ] company_manager có thể xem:")
    try:
        print("Branches:", list_branches("tongcongty")[:2])
        print("Meters:", list_meters("tongcongty")[:2])
    except Exception as e:
        print("READ company_manager error:", e)

    print("\n[READ] branch_manager có thể xem:")
    try:
        print("Branches:", list_branches("van_dau_mgr")[:2])
        print("Meters:", list_meters("van_dau_mgr")[:2])
    except Exception as e:
        print("READ branch_manager error:", e)

    print("\n[WRITE] company_manager tạo chi nhánh (PHẢI BỊ CHẶN):")
    try:
        create_branch("tongcongty", company_id, "An Dương", "Hải Phòng - An Dương")
        print("[UNEXPECTED] company_manager vẫn tạo được (sai)")
    except Exception as e:
        print("[OK] bị chặn:", e)

    print("\n[WRITE] branch_manager tạo đồng hồ (PHẢI BỊ CHẶN):")
    try:
        create_meter("van_dau_mgr", branch_ids["Văn Đẩu"], "Đồng hồ Văn Đẩu 03")
        print("[UNEXPECTED] branch_manager vẫn tạo được (sai)")
    except Exception as e:
        print("[OK] bị chặn:", e)

    print("\n[WRITE] admin tạo / sửa / xóa (ĐƯỢC PHÉP):")
    try:
        ok1 = create_meter("admin", branch_ids["Văn Đẩu"], "Đồng hồ Văn Đẩu 03")
        ok2 = update_meter("admin", branch_ids["Văn Đẩu"], "Đồng hồ Văn Đẩu 03", new_name="Đồng hồ Văn Đẩu 03 - NEW")
        ok3 = delete_meter("admin", branch_ids["Văn Đẩu"], "Đồng hồ Văn Đẩu 03 - NEW")
        print(f"[OK] admin: create={ok1}, update={ok2}, delete={ok3}")
    except Exception as e:
        print("[FAIL] admin write:", e)

    print("\n[USER-METER RELATIONSHIPS]:")
    user_meter_count = db.user_meter.count_documents({})
    print(f"Tổng quan hệ user-meter: {user_meter_count}")

    admin_meters = list(db.user_meter.find({"user_id": db.users.find_one({"username": "admin"})["_id"]}))
    print(f"Admin theo dõi {len(admin_meters)} meters")

    company_mgr_meters = list(db.user_meter.find({"user_id": db.users.find_one({"username": "tongcongty"})["_id"]}))
    print(f"Company manager theo dõi {len(company_mgr_meters)} meters")

    branch_mgr_meters = list(db.user_meter.find({"user_id": db.users.find_one({"username": "van_dau_mgr"})["_id"]}))
    print(f"Branch manager (Văn Đẩu) theo dõi {len(branch_mgr_meters)} meters")

    print("\nSeeding completed.")

if __name__ == "__main__":
    main()
