from typing import List, Optional
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base, generate_uuid

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    creation_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    # Relationships
    requirements: Mapped[List["Requirement"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    logical_units: Mapped[List["LogicalUnit"]] = relationship(back_populates="document", cascade="all, delete-orphan")
