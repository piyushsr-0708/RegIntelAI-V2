from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid
from datetime import datetime

class ManagementActionPlan(Base):
    __tablename__ = "management_action_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_controls.id"), index=True)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id"), index=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    description: Mapped[str] = mapped_column(String(2048))
    
    # Relationships
    control: Mapped["ComplianceControl"] = relationship(back_populates="maps")
    department: Mapped["Department"] = relationship(back_populates="maps")
    owner: Mapped[Optional["User"]] = relationship(back_populates="maps_owned")
