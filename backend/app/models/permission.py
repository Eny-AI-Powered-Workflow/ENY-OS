# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/permission.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    scope = Column(String, unique=True, index=True, nullable=False)

    # Relationships
    roles = relationship("RolePermission", back_populates="permission")