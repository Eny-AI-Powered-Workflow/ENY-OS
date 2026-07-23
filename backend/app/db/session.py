# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from app.db.base import Base

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function that yields a DB session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()