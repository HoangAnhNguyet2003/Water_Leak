from pydantic import BaseModel, Field
from typing import Optional

class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: Optional[str] = None

class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = None

class BranchOut(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
