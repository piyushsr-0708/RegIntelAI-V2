from sqlalchemy.orm import Session
from backend.database.repositories.verification_repository import VerificationRuleRepository

class VerificationService:
    def __init__(self, db: Session):
        self.repo = VerificationRuleRepository(db)
        
    # TODO: Implement business logic
