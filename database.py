from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ---------------------------
# SQLite + SQLAlchemy Setup
# ---------------------------

DATABASE_URL = "sqlite:///./members.db"
# if os.path.exists("members.db"):
#     os.remove("members.db")  # Remove existing database for fresh start
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    
    echo=True  # Set to True for SQL query logging
    )
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()