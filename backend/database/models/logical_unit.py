from typing import List, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid

JsonType = JSON().with_variant(JSONB, "postgresql")

class LogicalUnit(Base):
    __tablename__ = "logical_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    logical_unit_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    
    page_numbers: Mapped[list] = mapped_column(JsonType)
    hierarchy_node_ids: Mapped[list] = mapped_column(JsonType)
    block_ids: Mapped[list] = mapped_column(JsonType)
    
    # Relationships
    document: Mapped["Document"] = relationship(back_populates="logical_units")
    requirements: Mapped[List["Requirement"]] = relationship(back_populates="logical_unit")
