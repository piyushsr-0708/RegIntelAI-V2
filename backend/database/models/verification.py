from typing import List, Optional
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid
from datetime import datetime

class VerificationRule(Base):
    __tablename__ = "verification_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_controls.id"), index=True)
    
    rule_type: Mapped[str] = mapped_column(String(100))
    script_payload: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    expected_result: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    # Relationships
    control: Mapped["ComplianceControl"] = relationship(back_populates="verification_rules")
    results: Mapped[List["VerificationResult"]] = relationship(back_populates="rule", cascade="all, delete-orphan")

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("verification_rules.id"), index=True)
    
    execution_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50))
    actual_output: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    
    # Relationships
    rule: Mapped["VerificationRule"] = relationship(back_populates="results")
    evidence: Mapped[Optional["Evidence"]] = relationship(back_populates="result", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_controls.id"), index=True)
    result_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("verification_results.id"), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    
    file_path: Mapped[str] = mapped_column(String(1024))
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    result: Mapped[Optional["VerificationResult"]] = relationship(back_populates="evidence")
