
from pydantic import BaseModel, Field, model_validator
from typing import Optional

class UserCreate(BaseModel):
    user_name: str = Field(min_length=1, max_length=120)
    password_user: str = Field(min_length=6, max_length=120)
    role_name: str = Field(min_length=1, max_length=50)
    managed_water_meter: Optional[list[str]] = []
    branch_id: Optional[str] = None
    is_active: Optional[bool] = True

class UserUpdate(BaseModel):
    user_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    password_user: Optional[str]  = Field(default=None, min_length=6, max_length=120)
    role_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    managed_water_meter: Optional[list[str]] = None
    branch_id: Optional[str] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def at_least_one(self):
        if not any([
            self.user_name,
            self.password_user,
            self.role_name,
            self.managed_water_meter is not None,
            self.branch_id is not None,
            self.is_active is not None,
        ]):
            raise ValueError("At least one updatable field is required")
        return self

class UserOut(BaseModel):
    id: str
    branchId: Optional[str] = None
    username: str
    role_name: Optional[str] = None
    is_active: bool
