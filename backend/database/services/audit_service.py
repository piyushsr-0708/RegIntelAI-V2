"""
audit_service.py — RegIntel AI V2
Records state transitions to the audit_logs table.
Designed so notification hooks can be added later without changing callers.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session

from backend.database.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: Optional[str] = None,
        changes: Optional[list] = None,
    ) -> AuditLog:
        """
        entity_type: e.g. "MAP", "ASSIGNMENT", "USER"
        entity_id:   the PK of the affected entity
        action:      e.g. "APPROVED", "COMPLETED", "UPDATED"
        user_id:     who performed the action (nullable for system actions)
        changes:     list of {"field", "old", "new"} dicts
        """
        log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            changes=changes or [],
        )
        self.db.add(log)
        # Flush so the record is persisted in the same transaction
        self.db.flush()
        logger.info(f"AUDIT | {entity_type}/{entity_id} → {action} by {user_id or 'SYSTEM'}")
        return log

    def get_for_entity(self, entity_type: str, entity_id: str) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

    def get_recent(self, limit: int = 100) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )
