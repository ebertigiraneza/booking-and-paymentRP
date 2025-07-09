# shared/dependances.py
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from .databases import database
from .models import User, Wallet
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from shared.security import settings
from shared.schemas import WalletAuth

user_oauth2_scheme = HTTPBearer()

async def get_user(username: str) -> Optional[User]:
    query = User.__table__.select().where(User.username == username)
    return await database.fetch_one(query)



async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.USER_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_user_by_id(user_id: str) -> Optional[User]:
    query = User.__table__.select().where(User.id == user_id)
    return await database.fetch_one(query)

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.USER_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_wallet(
    wallet_auth: WalletAuth,
    current_user: User = Depends(get_current_user)):
    if not wallet_auth.address:
        raise HTTPException(status_code=400, detail="Wallet address is required")
    wallet = await database.fetch_one(
        Wallet.__table__.select().where(Wallet.address == wallet_auth.address)
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if wallet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this wallet")
    return wallet      


# This module provides dependencies for wallet access.----------------------------------------------------

# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def hash_wallet_password(password: str) -> str:
#     return pwd_context.hash(password)

# def verify_wallet_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)