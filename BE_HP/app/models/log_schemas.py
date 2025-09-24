from datetime import datetime
from enum import IntEnum
from typing import Optional
from pydantic import BaseModel, Field
from bson.objectid import ObjectId


class LogType(IntEnum):
    INFO = 1
    WARNING = 2
    ERROR = 3


class Log(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
    }

    id: Optional[ObjectId] = Field(default=None, alias="_id") 
    user_id: Optional[str] = None # None nếu là dự đoán từ mô hình
    create_time: Optional[datetime] = None
    log_type: LogType
    message: str
    source: Optional[str] = None
