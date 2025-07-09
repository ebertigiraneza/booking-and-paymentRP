# wallet/main.py
from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from shared.databases import database
from shared.models import Wallet
from shared.schemas import  WalletResponse, BalanceResponse, WalletAuth
import secrets
import string
import uuid
import random
from sqlalchemy import select
from shared.dependances import get_current_user
from shared.models import User, Wallet
from contextlib import asynccontextmanager


app = FastAPI(
    swagger_ui_init_oauth=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(tags=["Wallet"])

wordlist = [
    "chat", "arbre", "soleil", "lune", "rivière", "montagne", "neige", "voiture",
    "ordinateur", "bouteille", "musique", "poisson", "fleur", "papier", "chocolat"
]

def generate_passphrase(num_words: int = 12) -> str:
    return ' '.join(random.choice(wordlist) for _ in range(num_words))

def generate_address(length: int = 40) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

@router.get("/", response_model=list[WalletResponse], summary="Obtenir la liste des portefeuilles")
async def get_Wallets(current_user: User = Depends(get_current_user)):
    query = Wallet.__table__.select().where(Wallet.user_id == current_user.id)
    records = await database.fetch_all(query)
    return [WalletResponse(**dict(record)) for record in records]

@router.post("/create", summary="Créer un nouveau portefeuille")
async def create_new_Wallet(current_user: User = Depends(get_current_user)):
    id = str(uuid.uuid4())
    address = generate_address()
    password = generate_passphrase()
    user = current_user.username

    
    existing_user = await database.fetch_one(
        User.__table__.select().where(User.username == user)
    )
    if not existing_user:
        raise HTTPException(status_code=404, detail="Username not found")

    existing = await database.fetch_one(
        select(Wallet).where(Wallet.address == address)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Wallet already exists")
    
    Wallet_data = {
        "address": address,
        "wallet_password_hash": password,
        "user_id": existing_user.id,
        "balance": 1000.0,
        "currency": "Fbu"
    }
    # Note: Hashing the password is recommended for security, but here we use it as plain text for simplicity.
    
    # Wallet_data = {
    #     "address": address,
    #     "wallet_password_hash": hash_wallet_password(password),  # Hash sécurisé
    #     "user_id": current_user.id,
    #     "balance": 0.0
    # }
    
    query = Wallet.__table__.insert().values(**Wallet_data)
    await database.execute(query)
    
    return {"address": address, "password": password}

@router.post("/get_access/{address}", response_model=BalanceResponse, summary="Obtenir l'accès à un portefeuille")
async def get_access(
    address: str, 
    wallet_auth: WalletAuth,
    current_user: User = Depends(get_current_user)
):

    wallet = await database.fetch_one(
        select(Wallet).where(
            (Wallet.address == address) &
            (Wallet.user_id == current_user.id) &
            (Wallet.wallet_password_hash == wallet_auth.wallet_password)  # Vérification cruciale
        )
    )
    #  Note: Si vous avez une fonction de vérification de mot de passe, vous pouvez l'utiliser ici.
    # Récupérez d'abord le wallet
    # wallet = await database.fetch_one(
    #     select(Wallet).where(
    #         (Wallet.address == address) &
    #         (Wallet.user_id == current_user.id)
    #     )
    # )

    # # Puis vérifiez le mot de passe
    # if not wallet or not verify_wallet_password(wallet_auth.wallet_password, wallet["wallet_password_hash"]):
    #     raise HTTPException(...)
        
    if not wallet:
        raise HTTPException(
            status_code=403, 
            detail="Accès refusé : adresse ou mot de passe invalide"
        )
    
    return {
        "address": wallet["address"],
        "new_balance": wallet["balance"],
        "message": "Accès autorisé"
    }

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="API WALLET",
        version="1.0",
        routes=app.routes,
    )
    
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    
    openapi_schema["components"]["schemas"].update({
        "HTTPValidationError": {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "array",
                    "items": {
                        "$ref": "#/components/schemas/ValidationError"
                    }
                }
            }
        },
        "ValidationError": {
            "type": "object",
            "properties": {
                "loc": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "msg": {
                    "type": "string"
                },
                "type": {
                    "type": "string"
                }
            },
            "required": ["loc", "msg", "type"]
        }
    })
    
    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi