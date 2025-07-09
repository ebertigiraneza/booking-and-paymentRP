# shared/databases.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database

DATABASE_URL = "sqlite:///./booking.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async database interface
database = Database(DATABASE_URL)

Base = declarative_base()

async def connect_db():
    await database.connect()

async def disconnect_db():
    await database.disconnect()