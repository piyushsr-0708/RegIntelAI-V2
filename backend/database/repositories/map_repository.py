from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.map import ManagementActionPlan

class ManagementActionPlanRepository(BaseRepository[ManagementActionPlan]):
    def __init__(self, db: Session):
        super().__init__(ManagementActionPlan, db)
