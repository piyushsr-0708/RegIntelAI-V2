from typing import List, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="department")
    assignments: Mapped[List["ControlAssignment"]] = relationship(back_populates="department")
    maps: Mapped[List["ManagementActionPlan"]] = relationship(back_populates="department")

class ControlAssignment(Base):
    __tablename__ = "control_assignments"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_controls.id"), index=True)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id"), index=True)
    assigned_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    
    # Relationships
    control: Mapped["ComplianceControl"] = relationship(back_populates="assignments")
    department: Mapped["Department"] = relationship(back_populates="assignments")
    assigned_user: Mapped[Optional["User"]] = relationship(back_populates="assignments")
