from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MeterMeasurementOut(BaseModel):
    id: str
    meter_id: str
    measurement_time: datetime
    instant_flow: float
    instant_pressure: float
