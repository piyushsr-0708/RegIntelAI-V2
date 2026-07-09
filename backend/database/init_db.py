import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database.session import engine, SessionLocal
from backend.database.base import Base
import backend.database.models  # This imports all models so they register with Base.metadata

from backend.database.models import Role, Department

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
    
    db = SessionLocal()
    try:
        # Seed basic roles
        if not db.query(Role).first():
            print("Seeding roles...")
            db.add_all([
                Role(role_name="Admin", permissions=["*"]),
                Role(role_name="Compliance Officer", permissions=["read", "write"]),
                Role(role_name="Auditor", permissions=["read"])
            ])
            
        # Seed basic departments
        if not db.query(Department).first():
            print("Seeding departments...")
            db.add_all([
                Department(name="Compliance", description="Central Compliance Office"),
                Department(name="IT", description="Information Technology"),
                Department(name="Risk", description="Risk Management"),
                Department(name="Internal Audit", description="Internal Audit")
            ])
            
        db.commit()
        print("Seeding complete.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
