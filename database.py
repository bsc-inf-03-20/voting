from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ---------------------------
# SQLite + SQLAlchemy Setup
# ---------------------------

DATABASE_URL = "sqlite:///./voters.db"
if os.path.exists("voters.db"):
    os.remove("voters.db")  # Remove existing database for fresh start
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()