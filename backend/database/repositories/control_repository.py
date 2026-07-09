from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.control import ComplianceControl

class ComplianceControlRepository(BaseRepository[ComplianceControl]):
    def __init__(self, db: Session):
        super().__init__(ComplianceControl, db)
