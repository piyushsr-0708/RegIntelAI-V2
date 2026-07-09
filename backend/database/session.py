import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default to SQLite for V1, allows override for PostgreSQL later
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///d:/SuRaksha-v2/regintel.db")

# For SQLite, we need to enforce foreign keys
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for providing database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
