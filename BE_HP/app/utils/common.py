from typing import Any, Dict, Optional
from bson import ObjectId
from flask_jwt_extended import get_jwt
from ..extensions import get_db
from .bson import to_object_id, oid_str
from flask import jsonify, make_response
from urllib.parse import urlencode
from flask import current_app
from werkzeug.exceptions import NotFound
from pathlib import Path

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

def get_role_by_role_id(rid: str):
    db = get_db()
    r = db.roles.find_one({"_id": to_object_id(rid)})
    if not r: return None
    r["id"] = oid_str(r.pop("_id"))
    return r

def json_ok(payload, status: int = 200, headers: dict | None = None):
    resp = make_response(jsonify(payload), status)
    resp.headers.setdefault("Content-Type", "application/json; charset=utf-8")
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp

def created(resource_path: str, body: dict):
    return json_ok(body, 201, headers={"Location": resource_path})

def no_content():
    return ("", 204)

def parse_pagination(args):
    try:
        page = int(args.get("page", DEFAULT_PAGE))
    except Exception:
        page = DEFAULT_PAGE
    page = max(page, 1)

    try:
        page_size = int(args.get("page_size", DEFAULT_PAGE_SIZE))
    except Exception:
        page_size = DEFAULT_PAGE_SIZE
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    return page, page_size

def build_links(base_path: str, page: int, page_size: int, has_next: bool, extra_params: dict | None = None):
    extra_params = extra_params or {}
    links = []
    q_self = urlencode({**extra_params, "page": page, "page_size": page_size})
    links.append(f'<{base_path}?{q_self}>; rel="self"')
    if page > 1:
        q_prev = urlencode({**extra_params, "page": page-1, "page_size": page_size})
        links.append(f'<{base_path}?{q_prev}>; rel="prev"')
    if has_next:
        q_next = urlencode({**extra_params, "page": page+1, "page_size": page_size})
        links.append(f'<{base_path}?{q_next}>; rel="next"')
    return ", ".join(links)

def get_swagger_path(path: str):
    ROOT = Path(__file__).resolve().parents[1]
    SWAG_DIR = ROOT / 'swagger'

    p = SWAG_DIR / path
    return str(p)   

def get_branch_name_by_branch_id(branch_oid) -> str:
    """Map branch_id (oid string) sang branchName"""
    db = get_db()
    branch = db["branches"].find_one({"_id": branch_oid})
    if not branch:
        return None
    return branch.get("name", None)

def get_role_name_by_role_id(role_oid: str) -> str:
    """Map role_id (oid string) sang roleName"""
    db = get_db()
    role = db["roles"].find_one({"_id": ObjectId(role_oid)})
    if not role:
        return "branch_manager"  # fallback
    return role.get("role_name", "branch_manager")

def find_by_id(uid: str, COL: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        doc = db[COL].find_one({"_id": to_object_id(uid)})
    except Exception:
        return None
    if not doc: 
        return None
    doc["id"] = oid_str(doc.pop("_id"))
    return doc

def role_name() -> str | None:
    claims = get_jwt()
    return claims.get("role_name") if claims else None

def find_branch_by_name(branch_name: str) -> Dict[str, Any]:
    db = get_db()
    b = db.branches.find_one({"name": branch_name})
    print(f"Finding branch by name '{branch_name}':", b)
    if not b:
        raise NotFound(f"Branch '{branch_name}' not found")
    return b

def get_user_scope():
    claims = get_jwt()
    company_id = claims.get("company_id")
    branch_id  = claims.get("branch_id")
    role_id    = claims.get("role_id")
    role_name  = claims.get("role_name")
    return company_id, branch_id, role_id, role_name