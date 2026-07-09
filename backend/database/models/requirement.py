from typing import List, Optional
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid

class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    logical_unit_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("logical_units.id"), nullable=True)
    
    requirement_type: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(255))
    object_: Mapped[Optional[str]] = mapped_column("object", String(1024), nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    criticality: Mapped[str] = mapped_column(String(50), index=True, default="UNKNOWN")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Relationships
    document: Mapped["Document"] = relationship(back_populates="requirements")
    logical_unit: Mapped[Optional["LogicalUnit"]] = relationship(back_populates="requirements")
    controls: Mapped[List["ComplianceControl"]] = relationship(
        secondary="requirement_control_mapping",
        back_populates="requirements"
    )
