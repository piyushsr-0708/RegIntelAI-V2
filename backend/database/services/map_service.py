from sqlalchemy.orm import Session
from backend.database.repositories.map_repository import ManagementActionPlanRepository

class ManagementActionPlanService:
    def __init__(self, db: Session):
        self.repo = ManagementActionPlanRepository(db)
        
    # TODO: Implement business logic
