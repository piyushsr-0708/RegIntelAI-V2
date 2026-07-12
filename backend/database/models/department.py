from typing import List, Optional
from sqlalchemy import String, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid
from datetime import datetime

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

    # Link back to the MAP that generated this assignment
    map_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("management_action_plans.id"), nullable=True, index=True)

    # Assignment details carried over from the MAP
    title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    
    # Relationships
    control: Mapped["ComplianceControl"] = relationship(back_populates="assignments")
    department: Mapped["Department"] = relationship(back_populates="assignments")
    assigned_user: Mapped[Optional["User"]] = relationship(back_populates="assignments")
    map: Mapped[Optional["ManagementActionPlan"]] = relationship(back_populates="assignments")

