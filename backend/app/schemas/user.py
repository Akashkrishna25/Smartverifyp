"""Pydantic schemas for User."""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Literal

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "loan_officer"

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    # created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
