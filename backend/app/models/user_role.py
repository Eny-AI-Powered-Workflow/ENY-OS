# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/user_role.py
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)

    # Relationships
    # user = relationship("User", back_populates="roles")  # We don't have a User model
    # role = relationship("Role", back_populates="users")