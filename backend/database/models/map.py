from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid
from datetime import datetime

class ManagementActionPlan(Base):
    __tablename__ = "management_action_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_controls.id"), index=True)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id"), index=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Core
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    description: Mapped[str] = mapped_column(String(2048))

    # Priority & risk metadata
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)           # CRITICAL / HIGH / MEDIUM / LOW
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    automation_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # AI-generated content stored from pipeline
    ai_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source provenance — links back to original document / requirement text
    source_document_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_document_title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_requirement_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_requirement_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Reviewer annotations
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    control: Mapped["ComplianceControl"] = relationship(back_populates="maps")
    department: Mapped["Department"] = relationship(back_populates="maps")
    owner: Mapped[Optional["User"]] = relationship(back_populates="maps_owned")
    assignments: Mapped[list["ControlAssignment"]] = relationship(back_populates="map", cascade="all, delete-orphan")

