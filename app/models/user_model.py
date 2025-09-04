from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    mobile: str
    role: str
    ID: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str