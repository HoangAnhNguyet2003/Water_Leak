from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MeterCreate(BaseModel):
    branch_name: Optional[str] = None
    meter_name: str = Field(min_length=1, max_length=200)
    installation_time: Optional[datetime] = None

class MeterUpdate(BaseModel):
    branch_name: Optional[str] = None
    meter_name: Optional[str] = Field(None, min_length=1, max_length=200)
    installation_time: Optional[datetime] = None

class MeterOut(BaseModel):
    id: str
    branch_id: str
    meter_name: str
    installation_time: Optional[datetime] = None
