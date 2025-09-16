from .schemas import CompanyCreate
from . import repo
from ...errors import Conflict

def create_company(data: CompanyCreate):
    if repo.find_by_name(data.name):
        raise Conflict("Company name already exists")
    cid = repo.insert(data.model_dump())
    return repo.get(cid)

def get_company(cid: str):
    return repo.get(cid)
