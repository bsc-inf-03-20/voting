# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta

from database import SessionLocal, engine
from models import Voter
from auth import (
    hash_pin, verify_pin,
    create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from blockchain import Blockchain

# Create DB tables
import models
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
blockchain = Blockchain()
# Oauth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic schemas
class RegisterVoter(BaseModel):
    voter_id: str
    username: str
    pin: str
    name: str

class VoteInput(BaseModel):
    candidate: str

@app.get("/")
def root():
    return {"message": "Blockchain Voting API is running"}

@app.post("/register")
def register_voter(voter: RegisterVoter, db: Session = Depends(get_db)):
    if db.query(Voter).filter(Voter.voter_id == voter.voter_id).first():
        raise HTTPException(status_code=400, detail="Voter ID already registered.")
    if db.query(Voter).filter(Voter.username == voter.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")

    hashed_pin = hash_pin(voter.pin)
    new_voter = Voter(
        voter_id=voter.voter_id,
        username=voter.username,
        hashed_pin=hashed_pin,
        name=voter.name
    )
    db.add(new_voter)
    db.commit()
    return {"message": "Voter registered", "voter_id": voter.voter_id}

@app.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(Voter).filter(Voter.username == form_data.username).first()
    if not user or not verify_pin(form_data.password, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=token_expires
    )
    return {
        "access_token": token,
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
    user = db.query(Voter).filter(Voter.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="Voter not found.")
    if user.has_voted:
        raise HTTPException(status_code=400, detail="You have already voted.")

    blockchain.add_vote(user.voter_id, user.username, vote.candidate)
    print("Current votes in memory:", blockchain.current_votes)

    user.has_voted = True
    db.commit()

    return {
        "message": "Vote cast successfully",
        "candidate": vote.candidate,
        "pending_votes": len(blockchain.current_votes)
    }

@app.get("/users/me")
def get_profile(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(Voter).filter(Voter.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "voter_id": user.voter_id,
        "username": user.username,
        "name": user.name,
        "has_voted": user.has_voted
    }

@app.post("/mine")
def mine_block():
    if not blockchain.current_votes:
        raise HTTPException(status_code=400, detail="No votes to mine")
    
    previous_hash = blockchain.get_last_block()["hash"]
    block = blockchain.create_block(previous_hash)
    
    # Debug output
    print(f"Mined block contains {len(block['votes'])} votes")
    
    return {
        "message": "Block mined successfully",
        "block": block,
        "votes_included": len(block['votes'])
    }

@app.get("/chain")
def get_chain():
    return {"length": len(blockchain.chain), "chain": blockchain.chain}

@app.get("/count")
def count_votes():
    return {"vote_counts": blockchain.count_votes()}
