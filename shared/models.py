# shared/models.py
from sqlalchemy import Column, String, Float, Boolean, ForeignKey
from .databases import Base, database

class User(Base):
    """Table pour l'authentification globale"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class Wallet(Base):
    """Table pour les wallets indépendants"""
    __tablename__ = "wallets"
    
    address = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    wallet_password_hash = Column(String) 
    currency = Column(String)
    balance = Column(Float, default=0.0)
    is_locked = Column(Boolean, default=False)
    
class Transaction(Base):
    """Table pour les transactions"""
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True)
    wallet_address = Column(String, ForeignKey("wallets.address"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String)
    description = Column(String, nullable=True)
    status = Column(String)  # "pending", "completed", "failed"
    retry_count = Column(String , default=0)
    
class Booking(Base):
    """Table pour les reservations"""
    __tablename__ = "booking"
    
    id = Column(String, primary_key=True)
    target_book = Column(String, nullable=False)
    facture_id = Column(String)
    wallet_client = Column(String, ForeignKey("wallets.address"), nullable=False)
    amount = Column(Float, nullable=False)

    async def save(self, *args, **kwargs):
        if not self.facture_id:
            print("Génération de facture_id...")
            last_facture = await database.fetch_one(
                Booking.__table__.select().order_by(Booking.facture_id.desc()).limit(1)
            )
            if last_facture:
                last_code = last_facture.facture_id
                last_number = int(last_code.split('FA')[-1])
                self.facture_id = f'FA{last_number + 1:07d}'
                print(f"Nouveau facture_id : {self.facture_id}")
                while Booking.objects.filter(code=self.facture_id).exists():
                    last_number += 1
                    self.facture_id = f'FA{last_number:07d}'
                    print(f"Code déjà existant, nouveau code : {self.facture_id}")
            else:
                self.facture_id = 'FA0000001'
                print("Premier facture_id : FA0000001")
        super(Booking, self).save(*args, **kwargs)   
    
class BookingHold(Base):
    """Table pour les reservations en attente d'etre paye"""
    __tablename__ = "booking_hold"
    
    id = Column(String, primary_key=True)
    target_book = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  