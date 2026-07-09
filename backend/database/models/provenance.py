from typing import List
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid

# Use JSON on SQLite, JSONB on Postgres
JsonType = JSON().with_variant(JSONB, "postgresql")

class RequirementProvenance(Base):
    __tablename__ = "requirement_provenance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("requirements.id"), unique=True, index=True)
    
    logical_unit_id: Mapped[str] = mapped_column(String(255))
    page_numbers: Mapped[list] = mapped_column(JsonType)
    hierarchy_node_ids: Mapped[list] = mapped_column(JsonType)
    block_ids: Mapped[list] = mapped_column(JsonType)
    
    # Relationships
    requirement: Mapped["Requirement"] = relationship(back_populates="provenance")
