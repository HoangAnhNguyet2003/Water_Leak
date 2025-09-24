from ...models.log_schemas import Log, LogType
from ...utils import get_db, find_by_id
from ...extensions import socketio
import datetime

COL = 'logs'

def get_logs():
    db = get_db()
    logs_collection = db[COL]
    return [Log(**log) for log in logs_collection.find().sort("create_time", -1)]


def insert_log(message: str, log_type: LogType = LogType.INFO, user_id: str | None = None):
    db = get_db()
    logs_collection = db[COL]


    try:
        u = find_by_id(str(user_id), "users")
        resolved_source = u.get("username") if u else None
    except Exception:
        resolved_source = None

    doc = {
        "user_id": user_id,
        "create_time": datetime.datetime.now(),
        "log_type": int(log_type),
        "message": message,
        "source": resolved_source if resolved_source else None,
    }
    res = logs_collection.insert_one(doc)
    doc["_id"] = res.inserted_id

    payload = {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "create_time": doc["create_time"],
        "log_type": doc["log_type"],
        "message": doc["message"],
        "source": doc.get("source") if doc.get("source") else None,
    }

    try:
        socketio.emit("log", payload, room="admins")
    except Exception:
        pass

    return payload