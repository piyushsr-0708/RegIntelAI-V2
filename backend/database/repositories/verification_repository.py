from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.verification import VerificationRule

class VerificationRuleRepository(BaseRepository[VerificationRule]):
    def __init__(self, db: Session):
        super().__init__(VerificationRule, db)
