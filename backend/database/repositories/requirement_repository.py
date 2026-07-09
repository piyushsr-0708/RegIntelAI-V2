from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.requirement import Requirement

class RequirementRepository(BaseRepository[Requirement]):
    def __init__(self, db: Session):
        super().__init__(Requirement, db)
