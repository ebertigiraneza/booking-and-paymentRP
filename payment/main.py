# payment/main.py
from fastapi import FastAPI, HTTPException, Depends, APIRouter, Request
from pydantic import BaseModel
from shared.databases import database
from shared.models import Wallet, Transaction, Booking, User
import uuid
from sqlalchemy import select
from shared.dependances import get_current_user, get_current_wallet
from shared.models import User
from shared.schemas import WalletAuth
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from shared.databases import engine, Base
from shared.security import settings
import httpx
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(
    swagger_ui_init_oauth=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # Autorise tous les headers, y compris Authorization
)

router = APIRouter(tags=["Payement"])

class PaymentRequest(BaseModel):
    local_wallet: str  
    
# ----------------------------------------------------------- Payment -----------------------------------------------------------

@router.post("/payment", summary="Effectuer un paiement du facture ")
async def payment(
    request: PaymentRequest, id: str, current_user: User = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    async with httpx.AsyncClient() as client:
        try:
            token = credentials.credentials
            booking_response = await client.get(
                f"https://booking-and-paymentrp.fly.dev/booking/booking_hold/{id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
            booking_response.raise_for_status()
            booking = booking_response.json()
  
            status_default = "completed"
            wallet_password_check = await database.fetch_one(
                select(Wallet).where(
                    (Wallet.address == request.local_wallet)
                )
            )

            if not wallet_password_check:
                status_default = "failed"
                raise HTTPException(
                    status_code=403,
                    detail="Accès refusé : mot de passe du wallet invalide"
                )

            if wallet_password_check.balance < booking['amount']:
                raise HTTPException(status_code=400, detail="Solde Insuffisant")

            update_query = (
                Wallet.__table__
                .update()
                .where(Wallet.address == request.local_wallet)
                .values(balance=Wallet.balance - booking['amount'])
                .returning(Wallet.balance)
            )

            result = await database.fetch_one(update_query)

            transaction_data = {
                "id" :str(uuid.uuid4()),
                "wallet_address": request.local_wallet,
                "amount":booking['amount'],
                "transaction_type":"payment",
                "status": status_default,
                "description":f"Paiement de {booking['amount']} avec le compte {request.local_wallet}"
            }
            
            last_facture = await database.fetch_one(
                select(Booking.facture_id)
                .order_by(Booking.facture_id.desc())
                .limit(1)
            )

            if last_facture and last_facture.facture_id:
                last_number = int(last_facture.facture_id[2:])
                new_number = last_number + 1
                facture_id = f'FA{new_number:07d}'
            else:
                facture_id = 'FA0000001'

            booking_data ={
                "id": str(uuid.uuid4()),
                "target_book": booking['target_book'],
                "wallet_client": request.local_wallet,
                "amount": booking['amount'],
                "facture_id": facture_id
            }

            query_transaction = Transaction.__table__.insert().values(**transaction_data)
            await database.execute(query_transaction)

            query_booking = Booking.__table__.insert().values(**booking_data)
            await database.execute(query_booking)

            return {"message": "Paiement effectué", "amount": booking['amount'], "local_wallet": request.local_wallet}

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail="Service indisponible")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------- External Transfer -----------------------------------------------------------

class PartnerTransferRequest(BaseModel):
    partner_api_url: str  
    partner_wallet: str  
    amount: float
    callback_url: str 

# @app.post("/initiate-external-transfer")
async def external_transfer(
    request: PartnerTransferRequest,
    current_wallet: WalletAuth = Depends(get_current_wallet),
    current_user: User = Depends(get_current_user)
):
    status_default = "completed"
    if current_wallet.balance < request.amount:
        raise HTTPException(400, "Solde insuffisant")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{request.partner_api_url}/deposit",
                json={
                    "target_wallet": request.partner_wallet,
                    "amount": request.amount,
                    "metadata": {
                        "source_wallet": current_wallet.address,
                        "callback_url": request.callback_url
                    }
                }
            )
            
            if response.status_code != 200:
                status_default = "failed"
                raise HTTPException(502, "Échec du dépôt chez le partenaire")

    except httpx.RequestError:
        status_default = "failed"
        raise HTTPException(504, "Service partenaire indisponible")

    await database.execute(
        Wallet.__table__
        .update()
        .where(Wallet.address == current_wallet.address)
        .values(balance=Wallet.balance - request.amount)
    )
    
    transaction_data = {
        "id" :str(uuid.uuid4()),
        "wallet_address":current_wallet.address,
        "external_wallet": request.partner_wallet,
        "amount":request.amount,
        "transaction_type":"withdraw",
        "status": status_default,
        "description":f"Retrait de {request.amount} sur le compte {current_wallet.address}"
    }
    
    query_transaction = Transaction.__table__.insert().values(**transaction_data)
    await database.execute(query_transaction)

    return {"message": "Transfert initié", "partner_response": response.json()}


# --------------------------------------------------Gestion des transactions échouées --------------------------------------------------

from apscheduler.schedulers.background import BackgroundScheduler

async def retry_transaction(tx):
    try:
        await database.execute(
            Transaction.__table__
            .update()
            .where(Transaction.id == tx.id)
            .values(status="retried", retry_count=tx.retry_count + 1)
        )
    except Exception:
        await database.execute(
            Transaction.__table__
            .update()
            .where(Transaction.id == tx.id)
            .values(retry_count=tx.retry_count + 1)
        )

async def retry_failed_transactions():
    transactions = await database.fetch_all(
        select(Transaction)
        .where(Transaction.status == "failed")
        .where(Transaction.retry_count < 3)
    )
    
    for tx in transactions:
        await retry_transaction(tx)

scheduler = BackgroundScheduler()
scheduler.add_job(retry_failed_transactions, 'interval', minutes=30)
scheduler.start()

# ----------------------------------------------------------- swagger configuration -----------------------------------------------------------
# Configuration de Swagger pour corriger les références manquantes

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="API Withdraw",
        version="1.0",
        routes=app.routes,
    )
    
    # Correction des références manquantes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    
    # Ajoutez vos schémas manuellement si nécessaire
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