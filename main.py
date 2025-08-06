from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from auth import (
    hash_pin, 
    verify_pin, 
    create_access_token, 
    verify_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
import hashlib
import json
from blockchain import Blockchain
from time import time
import os

app = FastAPI()

# ---------------------------
# SQLite + SQLAlchemy Setup
# ---------------------------

DATABASE_URL = "sqlite:///./voters.db"
if os.path.exists("voters.db"):
    os.remove("voters.db")  # Remove existing database for fresh start
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ---------------------------
# Voter Database Model
# ---------------------------

class Voter(Base):
    __tablename__ = "voters"

    voter_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_pin = Column(String)
    name = Column(String)
    has_voted = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# Blockchain Voting System
# ---------------------------

blockchain = Blockchain()

# ---------------------------
# API Models
# ---------------------------

class RegisterVoter(BaseModel):
    voter_id: str
    username: str
    pin: str
    name: str

class LoginSchema(BaseModel):
    username: str
    pin: str

class VoteInput(BaseModel):
    candidate: str

# ---------------------------
# API Routes
# ---------------------------

@app.get("/")
def root():
    return {"message": "Blockchain Voting API is running"}

@app.post("/register")
def register_voter(voter: RegisterVoter, db: Session = Depends(get_db)):
    # Check if voter_id or username already exists
    existing_id = db.query(Voter).filter(Voter.voter_id == voter.voter_id).first()
    existing_user = db.query(Voter).filter(Voter.username == voter.username).first()
    
    if existing_id:
        raise HTTPException(status_code=400, detail="Voter ID already registered.")
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken.")
    
    # Hash the PIN
    hashed_pin = hash_pin(voter.pin)
    
    new_voter = Voter(
        voter_id=voter.voter_id,
        username=voter.username,
        hashed_pin=hashed_pin,
        name=voter.name,
        has_voted=False
    )
    
    db.add(new_voter)
    db.commit()
    return {
        "message": "Voter registered successfully",
        "voter_id": voter.voter_id,
        "username": voter.username
    }

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(Voter).filter(Voter.username == form_data.username).first()
    if not user or not verify_pin(form_data.password, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "voter_id": user.voter_id
    }

@app.post("/vote")
def vote(
    vote: VoteInput,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    voter = db.query(Voter).filter(Voter.username == current_user).first()
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found.")
    if voter.has_voted:
        raise HTTPException(status_code=400, detail="Voter has already voted.")
    
    blockchain.add_vote(voter.voter_id, current_user, vote.candidate)
    voter.has_voted = True
    db.commit()
    
    return {
        "message": "Vote cast successfully",
        "voter_id": voter.voter_id,
        "candidate": vote.candidate
    }

@app.get("/users/me")
async def read_users_me(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(Voter).filter(Voter.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "voter_id": user.voter_id,
        "username": user.username,
        "name": user.name,
        "has_voted": user.has_voted
    }

@app.post("/mine")
def mine_block():
    previous_hash = blockchain.get_last_block()["hash"]
    block = blockchain.create_block(previous_hash)
    return {"message": "New block created", "block": block}

@app.get("/chain")
def full_chain():
    return {"chain": blockchain.chain, "length": len(blockchain.chain)}

@app.get("/count")
def count_votes():
    return {"vote_counts": blockchain.count_votes()}