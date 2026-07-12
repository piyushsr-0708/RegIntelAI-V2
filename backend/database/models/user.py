from typing import List, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON, Boolean

JsonType = JSON().with_variant(JSONB, "postgresql")

class Role(Base):
    __tablename__ = "roles"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    role_name: Mapped[str] = mapped_column(String(100), unique=True)
    permissions: Mapped[list] = mapped_column(JsonType, default=list)
    
    users: Mapped[List["User"]] = relationship(back_populates="role")

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("departments.id"), nullable=True)
    role_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("roles.id"), nullable=True)
    
    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    role: Mapped[Optional["Role"]] = relationship(back_populates="users")
    assignments: Mapped[List["ControlAssignment"]] = relationship(back_populates="assigned_user")
    maps_owned: Mapped[List["ManagementActionPlan"]] = relationship(back_populates="owner")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")
