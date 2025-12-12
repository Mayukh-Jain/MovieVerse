from pydantic import BaseModel, EmailStr
from typing import Optional

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    
    # THIS IS THE FIX:
    # We set both configurations to support Pydantic V1 and V2
    class Config:
        from_attributes = True  # For Pydantic v2 (New)
        orm_mode = True         # For Pydantic v1 (Old/Fallback)

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None