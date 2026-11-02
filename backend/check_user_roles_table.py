#!/usr/bin/env python3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_user_roles_table():
    db = SessionLocal()
    try:
        # Check the structure of the user_roles table
        result = db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'user_roles'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        print("Columns in user_roles table:")
        for column in columns:
            print(f"  - {column[0]}: {column[1]}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user_roles_table()