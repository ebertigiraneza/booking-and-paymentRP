# shared/security.py
from pydantic import BaseModel

class SecuritySettings(BaseModel):
    USER_SECRET_KEY: str = "v2v3A2GGR0-iHUhLAE-bX5_w1HE8_ctkt287OgX0BGY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FAILURE_LIMIT : int = 3
    
settings = SecuritySettings()