from flask import Blueprint, request
from .schemas import CompanyCreate, CompanyOut
from .service import create_company, get_company
from ..common.response import created, json_ok
from ...errors import BadRequest

bp = Blueprint("companies", __name__)

@bp.post("/")
def create():
    try:
        data = CompanyCreate(**(request.get_json(silent=True) or {}))
    except Exception as e:
        raise BadRequest(str(e))
    c = create_company(data)
    return created(f"/api/v1/companies/{c['id']}", CompanyOut(**c).model_dump())

@bp.get("/<string:cid>")
def detail(cid):
    c = get_company(cid)
    return json_ok(CompanyOut(**c).model_dump()) if c else json_ok({"error":{"code":"NOT_FOUND","message":"Not found"}}, 404)
