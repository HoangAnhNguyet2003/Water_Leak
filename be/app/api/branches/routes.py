from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..meter.repo import _db_to_api
from ..authz.require import require_permissions, require_role
from .schemas import BranchCreate, BranchUpdate, BranchOut
from .service import create_branch, get_branch, list_branches, update_branch, remove_branch
from ...errors import BadRequest
from ..common.response import json_ok, created, no_content
from ..common.pagination import parse_pagination, build_links

bp = Blueprint("branches", __name__)

@bp.post("/")
@jwt_required()
@require_permissions("branch:create")
def create():
    try:
        data = BranchCreate(**(request.get_json(silent=True) or {}))
    except Exception as e:
        raise BadRequest(str(e))
    b = create_branch(data)
    print("Created branch:", b)
    return created(f"/api/v1/branches/{b['_id']}", BranchOut(**_db_to_api(b)).model_dump())

@bp.get("/get_all")
@jwt_required()
@require_role("admin")
def list_():
    page, page_size = parse_pagination(request.args)
    q = request.args.get("q")
    items, has_next = list_branches(page, page_size, q)
    # Return minimal fields: _id and name
    body = {"items": [{"_id": x.get("id") or str(x.get("_id")), "name": x.get("name")} for x in items], "page": page, "page_size": page_size}
    return json_ok(body)

@bp.get("/<string:bid>")
@jwt_required()
@require_permissions("branch:read")
def detail(bid):
    b = get_branch(bid)
    return json_ok(BranchOut(**b).model_dump()) if b else json_ok({"error":{"code":"NOT_FOUND","message":"Not found"}}, 404)

@bp.patch("/<string:bid>")
@jwt_required()
@require_permissions("branch:update")
def update(bid):
    try:
        data = BranchUpdate(**(request.get_json(silent=True) or {}))
    except Exception as e:
        raise BadRequest(str(e))
    b = update_branch(bid, data)
    return json_ok(BranchOut(**b).model_dump()) if b else json_ok({"error":{"code":"NOT_FOUND","message":"Not found"}}, 404)

@bp.delete("/<string:bid>")
@jwt_required()
@require_permissions("branch:delete")
def remove(bid):
    ok = remove_branch(bid)
    return json_ok() if ok else json_ok({"error":{"code":"NOT_FOUND","message":"Not found"}}, 404)
