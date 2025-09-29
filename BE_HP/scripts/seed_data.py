import os
import random
import pandas as pd
import re
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

def remove_vietnamese(text):
    patterns = {
        '[áàảãạăắằẳẵặâấầẩẫậ]': 'a',
        '[ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ]': 'A',
        '[éèẻẽẹêếềểễệ]': 'e',
        '[ÉÈẺẼẸÊẾỀỂỄỆ]': 'E',
        '[íìỉĩị]': 'i',
        '[ÍÌỈĨỊ]': 'I',
        '[óòỏõọôốồổỗộơớờởỡợ]': 'o',
        '[ÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢ]': 'O',
        '[úùủũụưứừửữự]': 'u',
        '[ÚÙỦŨỤƯỨỪỬỮỰ]': 'U',
        '[ýỳỷỹỵ]': 'y',
        '[ÝỲỶỸỴ]': 'Y',
        '[đ]': 'd',
        '[Đ]': 'D'
    }
    for pattern, repl in patterns.items():
        text = re.sub(pattern, repl, text)
    text = re.sub(r'\s+', '_', text)
    return text.lower()

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
def seed_companies():
    company = upsert("companies", {"name": "Công ty Cổ phần Cấp nước Hà Nội"}, {"name": "Công ty Cổ phần Cấp nước Hà Nội", "address": "Hà Nội"})
    return company["_id"]

def update_branches_company_id():
    company = db["companies"].find_one({"name": "Công ty Cổ phần Cấp nước Hà Nội"})
    if not company:
        company_id = seed_companies()
    else:
        company_id = company["_id"]
    
    db["branches"].update_many(
        {"company_id": {"$exists": False}},
        {"$set": {"company_id": company_id}}
    )

def seed_org():

    branches_df = pd.read_csv('./scripts/datafiles/branches.csv')
    branches_df.fillna('')
    branches = branches_df.to_dict(orient="records")
   
    branch_ids = {}
    for b in branches:
        doc = upsert("branches", {"name": b["name"], "address": b["address"]}, b)
        branch_ids[b["name"]] = doc["_id"]

    meters_df = pd.read_csv('./scripts/datafiles/meters.csv')
    meters_df = meters_df.fillna('')  
    meters = meters_df.to_dict(orient="records")

    meter_ids = {}
    for m in meters:
        branch_id = branch_ids[m["branch"]] if m["branch"] else None
    
        meter = {
            "branch_id": branch_id,
            "meter_name": m["meter_name"],
            "installation_time": m["installation_time"] if m["installation_time"] else None,
        }

        doc = upsert("meters", {"branch_id": meter["branch_id"], "meter_name": meter["meter_name"]}, meter)
        meter_ids[m["meter_name"]] = doc["_id"]

    return branch_ids, meter_ids

# ======================
# Seed: Users
# ======================
def seed_users(branch_ids: Dict[str, Any]):
    role_map = {r["role_name"]: r["_id"] for r in db.roles.find({}, {"role_name": 1})}
    
    users = [
        {"username": "admin",          "password": hash_password("Admin@123"),   "role_id": role_map["admin"],            "branch_id": None},
        {"username": "tongcongty",     "password": hash_password("Company@123"), "role_id": role_map["company_manager"],  "branch_id": None},
    ]
    
    branch_df = pd.read_csv('./scripts/datafiles/branches.csv')
    branch_df.fillna('')
    branch_list = branch_df.to_dict(orient="records") 

    for b in branch_list:
        user = {
            "username": remove_vietnamese(b['name']),
            "password": hash_password("Branch@123"),
            "role_id": role_map["branch_manager"],
            "branch_id": branch_ids.get(b["name"])
        }

        users.append(user)

    for u in users:
        upsert("users", {"username": u["username"]}, {**u, "is_active": True, "last_login": None})


# ======================
# Seed: User-Meter Relationships
# ======================
def seed_user_meter():
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
def seed_meter_measurements(meter_ids: Dict[str, Any]):
    docs = []
    measurement_df = pd.read_csv('./scripts/datafiles/measurements.csv')
    measurement_df.fillna('')
    measurement_data = measurement_df.to_dict(orient="records")

    for measurement in measurement_data: 
        meter_id = meter_ids.get(measurement["meter_name"])
        measurement_time = datetime.fromisoformat(measurement["measurement_time"])
        instant_flow = measurement["instant_flow"] if measurement["instant_flow"] != '' else None
        instant_pressure = measurement["instant_pressure"] if measurement["instant_pressure"] != '' else None

        doc = {
            "meter_id": meter_id,
            "measurement_time": measurement_time,
            "instant_flow": instant_flow,
            "instant_pressure": instant_pressure
        }
        docs.append(doc)

    if docs:
        db.meter_measurements.insert_many(docs)


def seed_meter_repairs(meter_ids: Dict[str, Any]):
    docs = []
    repair_df = pd.read_csv('./scripts/datafiles/repairs.csv')
    repair_df.fillna('')
    repair_data = repair_df.to_dict(orient="records")

    for repair in repair_data: 
        meter_id = meter_ids.get(repair["meter_name"])
        if not meter_id:
            continue  
        recorded_time = datetime.fromisoformat(repair['recorded_time']) if repair['recorded_time'] else None
        repair_time = datetime.fromisoformat(repair["repair_time"]) if repair["repair_time"] else None
        leak_reason = repair["leak_reason"] if repair["leak_reason"] != '' else "Unknown"
        replacement_type = repair["replacement_type"] if repair["replacement_type"] != '' else "Not specified"
        replacement_location = repair["replacement_location"] if repair["replacement_location"] != '' else "Not specified"
        
        doc = {
            "meter_id": meter_id,
            "recorded_time": recorded_time,
            "repair_time": repair_time,
            "leak_reason": leak_reason,
            "replacement_type": replacement_type,
            "replacement_location": replacement_location
        }
        docs.append(doc)

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


def seed_meter_consumptions(meter_ids: Dict[str, Any]):
    docs = []
    c_df = pd.read_csv('./scripts/datafiles/consumption.csv')
    c_df.fillna('')
    c_data = c_df.to_dict(orient="records")

    for c in c_data:
        meter_id = meter_ids.get(c["meter_name"])
        recording_date = c["date"]
        month = c["month"]
        consumption_value = c["monthly_consumption"] if c["monthly_consumption"] != '' else None

        doc = {
            "meter_id": meter_id,
            "recording_date": recording_date,
            "monthly_consumption": consumption_value, 
            "month": month
        }
        docs.append(doc)

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
    branch_ids, meter_ids = seed_org()
    update_branches_company_id()  
    seed_users(branch_ids)
    seed_user_meter()
    init_indexes(db)

    seed_meter_measurements(meter_ids)
    seed_meter_repairs(meter_ids)
    seed_predictions()
    seed_meter_consumptions(meter_ids)
    seed_meter_manual_thresholds()

    print("\nSeeding completed.")


if __name__ == "__main__":
    main()
