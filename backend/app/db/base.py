# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/db/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()

# Supabase owns auth.users; register its referenced key for ORM FK resolution.
Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
    extend_existing=True,
)