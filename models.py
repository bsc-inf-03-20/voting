from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class Voter(Base):
    __tablename__ = "voters"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_pin = Column(String, nullable=False)
    has_voted = Column(Boolean, default=False)
