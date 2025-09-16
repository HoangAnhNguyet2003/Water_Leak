from flask_jwt_extended import get_jwt, get_jwt_identity
from datetime import datetime, timezone
from bson import ObjectId
from werkzeug.exceptions import Forbidden
from .repo import list_logs, build_company_scope_query, find_log_by_id, delete_log_by_id, user_ids_in_company, insert_log
from werkzeug.exceptions import NotFound, BadRequest,  Unauthorized
from .schemas import LogCreate, LogOut

def _claims():
    c = get_jwt()
    return c.get("role_name") or c.get("role"), c.get("company_id")

def get_logs_scoped(page=1, limit=20, sort="created_time", order="desc"):
    role, company_id = _claims()
    if role == "admin":
        base = {}
    elif role in ("company_manager", "branch_manager"):
        if not company_id:
            raise Forbidden("Missing company scope")
        base = build_company_scope_query(company_id)
    else:
        raise Forbidden("Not allowed to view logs")
    return list_logs(base, page=page, limit=limit, sort=sort, order=order)

def delete_log_scoped(log_id: str) -> None:
    role, company_id = _claims()

    log_doc = find_log_by_id(log_id)
    if not log_doc:
        raise NotFound("Log not found")

    if role == "admin":
        pass  # ok
    elif role in ("company_manager", "branch_manager"):
        if not company_id:
            raise Forbidden("Missing company scope")
        allowed_users = set(user_ids_in_company(company_id))
        if log_doc.get("user_id") not in allowed_users:
            raise Forbidden("Not allowed to delete this log")
    else:
        raise Forbidden("Not allowed to delete logs")

    if not delete_log_by_id(log_id):
        # Rất hiếm khi tới đây (race condition)
        raise NotFound("Log not found")
    

def create_log_scoped(data: LogCreate) -> LogOut:
    # Phải đăng nhập
    identity = get_jwt_identity()
    if not identity:
        raise Unauthorized("Unauthorized")

    claims = get_jwt()
    # Lấy scope nếu có
    role_name  = claims.get("role_name") or claims.get("role")
    company_id = claims.get("company_id")
    branch_id  = claims.get("branch_id")

    payload = {
        "user_id": ObjectId(identity),
        "log_type": data.log_type.strip(),
        "severity": data.severity.strip(),
        "message": data.message.strip(),
        "created_time": datetime.now(timezone.utc),
    }
    if company_id:
        payload["company_id"] = ObjectId(company_id)
    if branch_id:
        payload["branch_id"]  = ObjectId(branch_id)
    if data.meta is not None:
        payload["meta"] = data.meta

    out = insert_log(payload)
    return LogOut(**out)