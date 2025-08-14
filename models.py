from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class Member(Base):
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    has_voted = Column(Boolean, default=False)
    verification_notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())