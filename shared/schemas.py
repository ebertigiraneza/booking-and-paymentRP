# shared/schemas.py
from pydantic import BaseModel
from typing import Optional

class WalletCreate(BaseModel):
    address: str
    password: str

class WalletResponse(BaseModel):
    address: str
    balance: float

    class Config:
        from_attributes = True


class WalletAuth(BaseModel):
    address: str
    wallet_password: str  
    
class BookingCreate(BaseModel):
    target_book: dict
    
class BookingResponse(BaseModel):
    id: str
    target_book: dict
    amount: float