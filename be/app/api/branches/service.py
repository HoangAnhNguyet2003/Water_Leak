from typing import Optional, Dict, Any
from flask_jwt_extended import get_jwt_identity
from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str
from ...errors import BadRequest
from .schemas import BranchCreate, BranchUpdate
from . import repo

def _get_user_scope():
    """Trả về (company_id, branch_id) của user hiện tại."""
    uid = get_jwt_identity()
    u = get_db().users.find_one({"_id": to_object_id(uid)}, {"company_id":1,"branch_id":1})
    return u.get("company_id"), u.get("branch_id")

def create_branch(data: BranchCreate):
    company_id, branch_id = _get_user_scope()
    # Nếu user bị khóa theo branch => không cho tạo chi nhánh (chỉ company_manager/admin)
    if branch_id:
        raise BadRequest("Not allowed: branch-scoped user cannot create branches")
    
    bid = repo.insert({
        "company_id": company_id,
        "name": data.name,
        "address": data.address
    })
    return repo.get(bid)

def get_branch(bid: str):
    company_id, branch_id = _get_user_scope()
    b = repo.get(bid)
    if not b: return None
    # branch scope: chỉ xem chính chi nhánh
    if branch_id and b["id"] != oid_str(branch_id):
        return None
    # company scope: chỉ xem chi nhánh thuộc company
    if company_id and b["company_id"] != oid_str(company_id):
        return None
    return b

def list_branches(page:int, page_size:int, q: Optional[str]):
    company_id, branch_id = _get_user_scope()
    # branch scope: chỉ trả về đúng chi nhánh của user
    if branch_id:
        one = repo.get(oid_str(branch_id))
        items = [one] if one else []
        return items, False
    # company scope: lọc theo company_id
    cid_str = oid_str(company_id) if company_id else None
    return repo.list_paginated(page, page_size, cid_str, q)

def update_branch(bid: str, data: BranchUpdate):
    company_id, branch_id = _get_user_scope()
    # branch scope: chỉ sửa chính chi nhánh
    if branch_id and bid != oid_str(branch_id):
        raise BadRequest("Not allowed to update another branch")
    b = repo.get(bid)
    if not b: return None
    if company_id and b["company_id"] != oid_str(company_id):
        raise BadRequest("Not allowed to update branch of another company")
    patch = {k:v for k,v in data.model_dump().items() if v is not None}
    if not patch:
        raise BadRequest("No fields to update")
    ok = repo.update(bid, patch)
    return ok and repo.get(bid)

def remove_branch(bid: str):
    company_id, branch_id = _get_user_scope()
    if branch_id and bid != oid_str(branch_id):
        return False
    b = repo.get(bid)
    if not b: return False
    if company_id and b["company_id"] != oid_str(company_id):
        return False
    return repo.delete(bid)
