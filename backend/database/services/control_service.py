from sqlalchemy.orm import Session
from backend.database.repositories.control_repository import ComplianceControlRepository

class ComplianceControlService:
    def __init__(self, db: Session):
        self.repo = ComplianceControlRepository(db)
        
    # TODO: Implement business logic
