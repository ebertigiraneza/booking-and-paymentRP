import bcrypt
import secrets

def hash_global_password(password: str) -> str:
    """Pour l'authentification utilisateur"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_global_password(password: str, hashed: str) -> bool:
    """Vérification mot de passe global"""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def hash_wallet_password(password: str) -> tuple[str, str]:
    """Pour les wallets (double sécurité)"""
    salt = secrets.token_hex(16)
    hashed = bcrypt.hashpw((password + salt).encode(), bcrypt.gensalt())
    return hashed.decode(), salt

def verify_wallet_password(password: str, hashed: str, salt: str) -> bool:
    """Vérification mot de passe wallet"""
    return bcrypt.checkpw((password + salt).encode(), hashed.encode())