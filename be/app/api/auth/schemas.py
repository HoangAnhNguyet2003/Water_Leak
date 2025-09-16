from pydantic import BaseModel, Field



class LoginIn(BaseModel):
    username: str
    password: str

class UserPublic(BaseModel):
    id: str
    username: str
    role_id: str | None = None
