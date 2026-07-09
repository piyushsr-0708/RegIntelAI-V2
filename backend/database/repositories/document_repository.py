from sqlalchemy.orm import Session
from backend.database.repositories.base import BaseRepository
from backend.database.models.document import Document

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)
