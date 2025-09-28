from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MeterManualThresholdOut(BaseModel):
    id: str
    meter_id: str
    set_time: datetime
    threshold_value: float

class MeterMeasurementOut(BaseModel):
    id: str
    meter_id: str
    measurement_time: datetime
    instant_flow: float
    instant_pressure: float
