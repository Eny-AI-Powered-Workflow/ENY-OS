# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/role.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)

    # Relationships
    permissions = relationship("RolePermission", back_populates="role")