from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RepairOut(BaseModel):
    id: str
    meterId: Optional[str] = None
    meterName: Optional[str] = None
    recordedTime: Optional[datetime] = None
    repairTime: Optional[datetime] = None
    leakReason: Optional[str] = None
    leakFix: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
