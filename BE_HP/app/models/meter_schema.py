from pydantic import BaseModel, ConfigDict, Field
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
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d")
        }
    )

    id: str
    branch_id: Optional[str] = None
    meter_name: str
    installation_time: Optional[datetime] = None
