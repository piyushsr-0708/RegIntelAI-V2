from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid

class RequirementControlMapping(Base):
    __tablename__ = "requirement_control_mapping"

    mapping_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("requirements.id"), index=True)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_controls.id"), index=True)


class ComplianceControl(Base):
    __tablename__ = "compliance_controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    objective: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str] = mapped_column(String(2048))
    
    control_type: Mapped[str] = mapped_column(String(100), index=True)
    implementation_category: Mapped[str] = mapped_column(String(100), index=True)
    frequency: Mapped[str] = mapped_column(String(50))
    automation_possible: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    requirements: Mapped[List["Requirement"]] = relationship(
        secondary="requirement_control_mapping",
        back_populates="controls"
    )
    assignments: Mapped[List["ControlAssignment"]] = relationship(back_populates="control", cascade="all, delete-orphan")
    verification_rules: Mapped[List["VerificationRule"]] = relationship(back_populates="control", cascade="all, delete-orphan")
    maps: Mapped[List["ManagementActionPlan"]] = relationship(back_populates="control", cascade="all, delete-orphan")
