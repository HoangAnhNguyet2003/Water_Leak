from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LogCreate(BaseModel):
    log_type: str = Field(min_length=1, max_length=50)   
    severity:  str = Field(min_length=1, max_length=20)  
    message:   str = Field(min_length=1, max_length=2000)
    meta: Optional[Dict[str, Any]] = None

class LogOut(BaseModel):
    id: str
    user_id: str
    log_type: str
    severity: str
    message: str
    created_time: str
    meta: Optional[Dict[str, Any]] = None
