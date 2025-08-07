from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class Voter(Base):
    __tablename__ = "voters"

    id = Column(Integer, primary_key=True, index=True)
    voter_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    # Ensure username is unique and indexed for fast lookups
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_pin = Column(String, nullable=False)
    has_voted = Column(Boolean, default=False)
