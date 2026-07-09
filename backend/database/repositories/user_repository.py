from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)
