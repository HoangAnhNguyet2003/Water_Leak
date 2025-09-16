from pydantic import BaseModel, Field
class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None

class CompanyOut(BaseModel):
    id: str
    name: str
    address: str | None = None
