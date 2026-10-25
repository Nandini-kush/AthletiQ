import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# DATABASE_URL is read from the environment; defaults to SQLite for local dev
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./athletiq.db")

engine = create_engine(
    DATABASE_URL,
    # SQLite needs this check_same_thread setting; ignored by PostgreSQL
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
