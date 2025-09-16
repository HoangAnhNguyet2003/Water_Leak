# app/api/auth/blocklist.py
from flask_jwt_extended import get_jwt, get_jwt_identity
from datetime import datetime, timezone
from ...extensions import get_db

BLACKLIST = set()

def _jwt_payload_to_doc(jwt_payload) -> dict:
    return {
        "jti": jwt_payload["jti"],
        "sub": jwt_payload.get("sub"),              # user id
        "type": jwt_payload.get("type"),            # "access" / "refresh"
        "exp": datetime.fromtimestamp(jwt_payload["exp"], tz=timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }

def add_current_token_to_blocklist():
    payload = get_jwt()
    doc = _jwt_payload_to_doc(payload)
    get_db().jwt_blocklist.update_one(
        {"jti": doc["jti"]},
        {"$setOnInsert": doc},
        upsert=True
    )
