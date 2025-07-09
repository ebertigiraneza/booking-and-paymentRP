# booking/main.py

from fastapi import FastAPI, Depends, APIRouter, HTTPException
from shared.databases import database, Base, engine
from shared.models import BookingHold, User, Booking
from shared.dependances import get_current_user
import uuid
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from shared.schemas import BookingCreate, BookingResponse
import json

app = FastAPI(swagger_ui_init_oauth=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(tags=["Booking"])

@router.post("/booking", response_model=BookingResponse, summary=" Create a Booking order")
async def create_booking(booking: BookingCreate, current_user: User = Depends(get_current_user)):
    booking_id = str(uuid.uuid4())
    target_book = booking.target_book  
    query = BookingHold.__table__.insert().values(
        id=booking_id,
        target_book=json.dumps(target_book),
        amount=sum(target_book.values())
    )
    
    await database.execute(query)
    return {"target_book": target_book, "id": booking_id, "amount": sum(target_book.values())}

@router.get("/booking_hold/{id:str}", summary="Get a booking hold by ID")
async def get_booking_hold(id: str, current_user: User = Depends(get_current_user)):
    query = BookingHold.__table__.select().where(BookingHold.id == id)
    booking = await database.fetch_one(query)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"booking_id": booking.id, "target_book": booking.target_book, "amount": booking.amount}

@router.get("/booking/{id:str}", summary="Get a booking by ID")
async def get_booking(id: str, current_user: User = Depends(get_current_user)):
    query = Booking.__table__.select().where(Booking.id == id)
    booking = await database.fetch_one(query)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"booking_id": booking.id, "target_book": booking.target_book, "amount": booking.amount, "facture": booking.facture_id, "wallet": booking.wallet_client}