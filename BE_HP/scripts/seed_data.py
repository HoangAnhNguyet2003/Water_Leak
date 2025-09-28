import os
import random
from datetime import datetime, timezone, timedelta, time
import bcrypt as bc
from pymongo import MongoClient, ASCENDING, DESCENDING, ReturnDocument
from typing import Optional, Dict, Any, List

# ======================
# Cấu hình kết nối MongoDB
# ======================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB  = os.getenv("MONGO_DB", "Nuoc_HP")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]


# ======================
# Helper Functions
# ======================
def hash_password(plain: str) -> str:
    return bc.hashpw(plain.encode("utf-8"), bc.gensalt()).decode("utf-8")


def upsert(collection: str, query: Dict[str, Any], doc: Dict[str, Any]):
    return db[collection].find_one_and_update(
        query, {"$setOnInsert": doc}, upsert=True, return_document=ReturnDocument.AFTER
    )


def _norm_keys(keys):
    return tuple((k, int(v)) for k, v in keys)


def ensure_index(coll, keys, name: str, **opts):
    info = coll.index_information()
    if name in info:
        if _norm_keys(info[name]["key"]) != _norm_keys(keys):
            coll.drop_index(name)
            return coll.create_index(keys, name=name, **opts)
        return name
    return coll.create_index(keys, name=name, **opts)


# ======================
# Reset & Indexing
# ======================
def reset_collections():
    print("Resetting collections...")
    collections = [
        "companies", "branches", "meters",
        "users", "roles", "user_meter",
        "meter_manual_thresholds", "meter_consumptions",
        "meter_repairs", "meter_measurements",
        "ai_models", "predictions", "logs"
    ]
    for col in collections:
        db[col].drop()

    for col_name in db.list_collection_names():
        for idx_name in list(db[col_name].index_information().keys()):
            if idx_name != "_id_":
                db[col_name].drop_index(idx_name)


def init_indexes(db):
    # Users / Roles
    ensure_index(db.users, [("username", ASCENDING)], unique=True, name="uniq_user_username")
    ensure_index(db.roles, [("role_name", ASCENDING)], unique=True, name="uniq_role_name")

    # Company–Branch–Meter
    ensure_index(db.companies, [("name", ASCENDING)], unique=True, name="uniq_company_name")
    ensure_index(db.branches,  [("company_id", ASCENDING)], name="idx_branch_company")
    ensure_index(db.branches,  [("name", ASCENDING)], name="idx_branch_name")
    ensure_index(db.meters,    [("branch_id", ASCENDING)], name="idx_meter_branch")
    ensure_index(db.meters,    [("meter_name", ASCENDING)], name="idx_meter_name")

    # User–Meter
    ensure_index(db.user_meter, [("user_id", ASCENDING)], name="idx_um_user")
    ensure_index(db.user_meter, [("meter_id", ASCENDING)], name="idx_um_meter")
    ensure_index(db.user_meter,
                 [("user_id", ASCENDING), ("meter_id", ASCENDING)],
                 unique=True, name="uniq_um")

    # Meter data
    ensure_index(db.meter_manual_thresholds,
                 [("meter_id", ASCENDING), ("set_time", DESCENDING)],
                 name="idx_thresh_meter_time")
    ensure_index(db.meter_consumptions,
                 [("meter_id", ASCENDING), ("recording_date", DESCENDING)],
                 name="idx_consume_meter_month")
    ensure_index(db.meter_repairs,
                 [("meter_id", ASCENDING), ("repair_time", DESCENDING)],
                 name="idx_repair_meter_time")
    ensure_index(db.meter_measurements,
                 [("meter_id", ASCENDING), ("measurement_time", DESCENDING)],
                 name="idx_meas_meter_time")

    # AI & Prediction
    ensure_index(db.ai_models,   [("name", ASCENDING)], unique=True, name="uniq_model_name")
    ensure_index(db.predictions, [("meter_id", ASCENDING), ("prediction_time", DESCENDING)],
                 name="idx_pred_meter_time")
    ensure_index(db.predictions, [("model_id", ASCENDING)], name="idx_pred_model")


# ======================
# Seed: Roles
# ======================
def seed_roles():
    roles = [
        {"role_name": "admin"},
        {"role_name": "company_manager"},
        {"role_name": "branch_manager"},
    ]
    for r in roles:
        upsert("roles", {"role_name": r["role_name"]}, r)


# ======================
# Seed: Organization
# ======================
def seed_org():
    comp = upsert("companies", {"name": "Công ty Cấp Nước Hải Phòng"},
                  {"name": "Công ty Cấp Nước Hải Phòng", "address": "Hải Phòng"})
    company_id = comp["_id"]

    branches = [
        {"company_id": company_id, "name": "Văn Đẩu",    "address": "Hải Phòng - Văn Đẩu"},
        {"company_id": company_id, "name": "Bắc Sơn",    "address": "Hải Phòng - Bắc Sơn"},
        {"company_id": company_id, "name": "Trường Sơn", "address": "Hải Phòng - Trường Sơn"},
    ]
    branch_ids = {}
    for b in branches:
        doc = upsert("branches", {"company_id": b["company_id"], "name": b["name"]}, b)
        branch_ids[b["name"]] = doc["_id"]

    # Tạo 10 đồng hồ
    meters = []
    base_dates = {
        "Văn Đẩu": datetime(2023, 5, 1),
        "Bắc Sơn": datetime(2023, 6, 1),
        "Trường Sơn": datetime(2023, 7, 1),
    }

    for branch_name, count in [("Văn Đẩu", 4), ("Bắc Sơn", 3), ("Trường Sơn", 3)]:
        branch_id = branch_ids[branch_name]
        base_date = base_dates[branch_name]
        for i in range(1, count + 1):
            meters.append({
                "branch_id": branch_id,
                "meter_name": f"Đồng hồ {branch_name} {i:02d}",
                "installation_time": base_date + timedelta(days=10 * (i - 1))
            })

    for m in meters:
        upsert("meters", {"branch_id": m["branch_id"], "meter_name": m["meter_name"]}, m)

    return company_id, branch_ids


# ======================
# Seed: Users
# ======================
def seed_users(company_id, branch_ids: Dict[str, Any]):
    role_map = {r["role_name"]: r["_id"] for r in db.roles.find({}, {"role_name": 1})}

    users = [
        {"username": "admin",          "password": hash_password("Admin@123"),   "role_id": role_map["admin"],            "branch_id": None},
        {"username": "tongcongty",     "password": hash_password("Company@123"), "role_id": role_map["company_manager"],  "company_id": company_id, "branch_id": None},
        {"username": "van_dau_mgr",    "password": hash_password("Branch@123"),  "role_id": role_map["branch_manager"],   "branch_id": branch_ids["Văn Đẩu"]},
        {"username": "bac_son_mgr",    "password": hash_password("Branch@123"),  "role_id": role_map["branch_manager"],   "branch_id": branch_ids["Bắc Sơn"]},
        {"username": "truong_son_mgr", "password": hash_password("Branch@123"),  "role_id": role_map["branch_manager"],   "branch_id": branch_ids["Trường Sơn"]},
    ]

    for u in users:
        upsert("users", {"username": u["username"]}, {**u, "is_active": True, "last_login": None})


# ======================
# Seed: User-Meter Relationships
# ======================
def seed_user_meter(company_id, branch_ids: Dict[str, Any]):
    users = list(db.users.find({}, {"_id": 1, "username": 1, "role_id": 1, "branch_id": 1}))
    meters = list(db.meters.find({}, {"_id": 1, "branch_id": 1}))
    roles = {r["_id"]: r["role_name"] for r in db.roles.find({}, {"_id": 1, "role_name": 1})}

    db.user_meter.delete_many({})
    user_meter_docs = []

    for user in users:
        role_name = roles.get(user["role_id"])
        if role_name == "company_manager":
            for meter in meters:
                user_meter_docs.append({"user_id": user["_id"], "meter_id": meter["_id"]})
        elif role_name == "branch_manager":
            user_branch_id = user.get("branch_id")
            if user_branch_id:
                for meter in meters:
                    if meter["branch_id"] == user_branch_id:
                        user_meter_docs.append({"user_id": user["_id"], "meter_id": meter["_id"]})

    if user_meter_docs:
        db.user_meter.insert_many(user_meter_docs)
        print(f"✅ Đã tạo {len(user_meter_docs)} quan hệ user-meter")


# ======================
# Seed: Domain Data
# ======================
def seed_meter_measurements():
    print("Seeding meter_measurements ...")
    meters = list(db.meters.find({}, {"_id": 1}))
    docs = []
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=13)).date()  
    hourly_template = [
        6.0, 4.9, 5.2, 6.4, 8.0, 12.6, 27.5, 25.6, 19.7, 18.2, 19.6, 18.6,
        17.3, 13.7, 13.7, 15.9, 17.8, 30.9, 37.6, 31.1, 25.4, 19.7, 15.2, 9.5
    ]

    for idx, m in enumerate(meters):
        meter_offset = random.uniform(-0.2, 0.3)
        for day_offset in range(14):
            day = start_date + timedelta(days=day_offset)
            for hour in range(24):
                ts = datetime.combine(day, time(hour, 0, 0, tzinfo=timezone.utc))
                mean_flow = hourly_template[hour] + meter_offset

                flow = round(max(0.0, random.gauss(mean_flow, 0.25)), 3)
                pressure = round(random.uniform(1.60, 1.95), 3)
                docs.append({
                    "meter_id": m["_id"],
                    "measurement_time": ts,
                    "instant_flow": flow,
                    "instant_pressure": pressure,
                })
    if docs:
        db.meter_measurements.insert_many(docs)


def seed_meter_repairs():
    print("Seeding meter_repairs ...")
    meters = list(db.meters.find({}, {"_id": 1}))
    reasons = ["sensor_error", "leak_fix", "pipe_crack", "calibration"]
    locations = ["pit_A1", "street_12", "junction_B3", "station_C"]
    types = ["temporary", "full"]

    docs = []
    base = datetime.now(timezone.utc) - timedelta(days=180)
    for m in meters:
        for _ in range(random.choice([1, 1, 2])):
            recorded = base + timedelta(days=random.randint(0, 150), hours=random.randint(0, 23))
            repair   = recorded + timedelta(hours=random.randint(1, 48))
            docs.append({
                "meter_id": m["_id"],
                "recorded_time": recorded,
                "repair_time": repair,
                "leak_reason": random.choice(reasons),
                "replacement_location": random.choice(locations),
                "replacement_type": random.choice(types),
            })
    if docs:
        db.meter_repairs.insert_many(docs)


def seed_predictions():
    print("Seeding predictions ...")
    meters = list(db.meters.find({}, {"_id": 1}))
    labels = ["normal", "leak"]

    model = upsert("ai_models", {"name": "demo_model_v1"}, {"name": "demo_model_v1"})
    model = upsert("ai_models",  {"name": "lstm_autoencoder"}, {"name": "lstm_autoencoder"})
    model_id = model["_id"]

    docs = []
    for m in meters:
        measurements = list(db.meter_measurements.find({"meter_id": m["_id"]}, {"measurement_time": 1, "instant_flow": 1}))
        if not measurements:
            continue
        for meas in measurements:
            ts = meas.get("measurement_time")
            flow = meas.get("instant_flow") if meas.get("instant_flow") is not None else round(random.uniform(2.0, 3.2), 2)

            label = random.choices(labels, weights=[0.5, 0.5], k=1)[0]
            docs.append({
                "meter_id": m["_id"],
                "model_id": model_id,
                "prediction_time": ts,
                "predicted_threshold": round(random.uniform(1.8, 2.2), 2),
                "predicted_label": label,
                "confidence": round(random.uniform(0.6, 0.98), 2),
                "recorded_instant_flow": flow
            })
    if docs:
        # Insert in reasonable batch sizes to avoid very large single insert
        batch_size = 1000
        for i in range(0, len(docs), batch_size):
            db.predictions.insert_many(docs[i:i+batch_size])


def seed_meter_consumptions():
    print("Seeding meter_consumptions ...")
    meters = list(db.meters.find({}, {"_id": 1}))
    docs = []
    now = datetime.now(timezone.utc)

    for m in meters:
        for i in range(6):
            month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            recording_date = month_start
            monthly_consumption = round(random.uniform(500, 3000), 2)
            docs.append({
                "meter_id": m["_id"],
                "recording_date": recording_date,
                "monthly_consumption": monthly_consumption
            })

    if docs:
        db.meter_consumptions.insert_many(docs)


def seed_meter_manual_thresholds():
    print("Seeding meter_manual_thresholds ...")
    meters = list(db.meters.find({}, {"_id": 1}))
    docs = []
    now = datetime.now(timezone.utc)

    for m in meters:
        num_thresholds = random.randint(1, 3)
        for _ in range(num_thresholds):
            days_ago = random.randint(0, 90)
            set_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            threshold_value = round(random.uniform(1.5, 4.0), 3)
            docs.append({
                "meter_id": m["_id"],
                "set_time": set_time,
                "threshold_value": threshold_value
            })

    if docs:
        db.meter_manual_thresholds.insert_many(docs)


# ======================
# Main Execution
# ======================
def main():
    print(f"Connecting to {MONGO_URI}, DB={MONGO_DB}")
    reset_collections()
    seed_roles()
    company_id, branch_ids = seed_org()
    seed_users(company_id, branch_ids)
    seed_user_meter(company_id, branch_ids)
    init_indexes(db)

    seed_meter_measurements()
    seed_meter_repairs()
    seed_predictions()
    seed_meter_consumptions()
    seed_meter_manual_thresholds()

    print("\nSeeding completed.")


if __name__ == "__main__":
    main()
