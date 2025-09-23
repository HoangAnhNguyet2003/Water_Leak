from pymongo import MongoClient, ASCENDING, DESCENDING
from flask import current_app, g
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO


jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def get_db():
    if "mongo_client" not in g:
        uri = current_app.config["MONGO_URI"]
        g.mongo_client = MongoClient(uri)
    client = g.mongo_client
    dbname = current_app.config["MONGO_DB"]
    return client[dbname]


def init_indexes(db):
    # Users & AuthZ
   
    db.users.create_index([("username", ASCENDING)], unique=True, name="uniq_user_username")
    db.roles.create_index([("role_name", ASCENDING)], unique=True, name="uniq_role_name")

    # Company–Branch–Meter
    db.companies.create_index([("name", ASCENDING)], unique=True, name="uniq_company_name")
    db.branches.create_index([("company_id", ASCENDING)], name="idx_branch_company")
    db.branches.create_index([("name", ASCENDING)], name="idx_branch_name")
    db.meters.create_index([("branch_id", ASCENDING)], name="idx_meter_branch")
    db.meters.create_index([("meter_name", ASCENDING)], name="idx_meter_name")

    # User–Meter (n–n)
    db.user_meter.create_index([("user_id", ASCENDING)], name="idx_um_user")
    db.user_meter.create_index([("meter_id", ASCENDING)], name="idx_um_meter")
    db.user_meter.create_index(
        [("user_id", ASCENDING), ("meter_id", ASCENDING)],
        unique=True,
        name="uniq_um" 
    )

    # Meter data
    db.meter_manual_thresholds.create_index([("meter_id", ASCENDING), ("set_time", DESCENDING)], name="idx_thresh_meter_time")
    db.meter_consumptions.create_index([("meter_id", ASCENDING), ("recording_date", DESCENDING)], name="idx_consume_meter_month")
    db.meter_repairs.create_index([("meter_id", ASCENDING), ("repair_time", DESCENDING)], name="idx_repair_meter_time")
    db.meter_measurements.create_index([("meter_id", ASCENDING), ("measurement_time", DESCENDING)], name="idx_meas_meter_time")

    # AI & Prediction & Alert
    db.ai_models.create_index([("name", ASCENDING)], unique=True, name="uniq_model_name")
    db.predictions.create_index([("meter_id", ASCENDING), ("prediction_time", DESCENDING)], name="idx_pred_meter_time")
    db.predictions.create_index([("model_id", ASCENDING)], name="idx_pred_model")
    db.roles.create_index([("role_name", ASCENDING)], unique=True, name="uniq_role_name")


def close_db(e=None):
    client = g.pop("mongo_client", None)
    if client:
        client.close()

TOKEN_BLOCKLIST = set()
socketio = SocketIO()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in TOKEN_BLOCKLIST