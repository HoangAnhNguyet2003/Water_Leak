from pydantic import BaseModel, Field
from typing import Optional

class MeterRepairSchema(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    meter_id: str
    recorded_time: str
    repair_time: str
    leak_reason: Optional[str] = None
    replacement_location: Optional[str] = None
    replacement_type: Optional[str] = None

class MeterRepairCreateSchema(BaseModel):
    meter_id: str
    recorded_time: str
    repair_time: str
    leak_reason: Optional[str] = None
    replacement_location: Optional[str] = None
    replacement_type: Optional[str] = None
