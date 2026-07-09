from sqlalchemy.orm import Session
from backend.database.repositories.document_repository import DocumentRepository

class DocumentService:
    def __init__(self, db: Session):
        self.repo = DocumentRepository(db)
        
    # TODO: Implement business logic
