from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from .branch_utils import list_branches
from ...require import require_role
from ...utils import parse_pagination, json_ok, get_swagger_path
from flasgger import swag_from

branch_bp = Blueprint("branches", __name__)

@branch_bp.get("/get_all")
@swag_from(get_swagger_path('branches/get_all.yml'))
@jwt_required()
@require_role("admin")
def list_():
    page, page_size = parse_pagination(request.args)
    q = request.args.get("q")
    items, has_next = list_branches(page, page_size, q)
    # Return minimal fields: _id and name
    body = {"items": [{"_id": x.get("id") or str(x.get("_id")), "name": x.get("name")} for x in items], "page": page, "page_size": page_size}
    return json_ok(body)