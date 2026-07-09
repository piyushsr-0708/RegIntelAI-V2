from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.department import Department

class DepartmentRepository(BaseRepository[Department]):
    def __init__(self, db: Session):
        super().__init__(Department, db)
