# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/kajabi_connection.py
import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class KajabiConnection(Base):
    __tablename__ = "kajabi_connections"
    __table_args__ = (
        CheckConstraint("shared_slot = 1", name="kajabi_connections_shared_slot_check"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shared_slot = Column(SmallInteger, nullable=False, unique=True, default=1)
    client_id_encrypted = Column(Text, nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)
    site_id_encrypted = Column(Text, nullable=False)
    last_validated_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
