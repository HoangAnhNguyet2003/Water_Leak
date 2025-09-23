from flask_jwt_extended import get_jwt
from werkzeug.exceptions import Forbidden, BadRequest
from .repo import overview_counts

def _claims():
    c = get_jwt()
    return c.get("role_name") or c.get("role"), c.get("company_id"), c.get("branch_id")

def get_overview_scoped() -> dict:
    role, company_id, _ = _claims()

    if role == "admin":
        # toàn hệ thống
        return overview_counts(company_id=None)

    if role in ("company_manager", "branch_manager"):
        if not company_id:
            raise BadRequest("Your token has no company_id")
        # gộp phạm vi theo công ty
        return overview_counts(company_id=str(company_id))

    # các role khác (nếu có) không được xem
    raise Forbidden("You are not allowed to view overview")
