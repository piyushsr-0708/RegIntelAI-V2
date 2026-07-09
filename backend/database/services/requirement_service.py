from sqlalchemy.orm import Session
from backend.database.repositories.requirement_repository import RequirementRepository

class RequirementService:
    def __init__(self, db: Session):
        self.repo = RequirementRepository(db)
        
    # TODO: Implement business logic
