# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/role_permission.py
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)

    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")