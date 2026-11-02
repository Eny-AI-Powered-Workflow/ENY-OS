#!/usr/bin/env python3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_tables():
    db = SessionLocal()
    try:
        # List all tables in the public schema
        result = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        print("Tables in public schema:")
        for table in tables:
            print(f"  - {table[0]}")
    finally:
        db.close()

if __name__ == "__main__":
    check_tables()