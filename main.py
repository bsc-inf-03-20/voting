from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from auth  import hash_pin, verify_pin
from models import Voter
import hashlib
import json
from time import time
from blockchain import Blockchain

app = FastAPI()
# Base.metadata.create_all(bind=engine)

blockchain = Blockchain()

# ---------------------------
# SQLite + SQLAlchemy Setup
# ---------------------------

DATABASE_URL = "sqlite:///./voters.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------------------------
# Voter Database Model
# ---------------------------

class Voter(Base):
    __tablename__ = "voters"

    voter_id = Column(String, primary_key=True, index=True)
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

# Session (simulate)
logged_in_users = {}

# Pydantic Schemas
class RegisterSchema(BaseModel):
    username: str
    pin: str

class LoginSchema(BaseModel):
    username: str
    pin: str

class VoteSchema(BaseModel):
    username: str
    candidate: str

# ---------------------------
# Blockchain Voting System
# ---------------------------

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.create_block(previous_hash='1')  # Genesis block

    def create_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'votes': self.current_votes,
            'previous_hash': previous_hash,
        }
        block['hash'] = self.hash_block(block)
        self.chain.append(block)
        self.current_votes = []
        return block

    def add_vote(self, voter_id, candidate):
        vote = {'voter_id': voter_id, 'candidate': candidate}
        self.current_votes.append(vote)
        return vote

    def hash_block(self, block):
        block_copy = block.copy()
        block_copy.pop('hash', None)
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def get_last_block(self):
        return self.chain[-1]

    def count_votes(self):
        tally = {}
        for block in self.chain:
            for vote in block['votes']:
                candidate = vote['candidate']
                tally[candidate] = tally.get(candidate, 0) + 1
        return tally

blockchain = Blockchain()

# ---------------------------
# API Models
# ---------------------------

class RegisterVoter(BaseModel):
    voter_id: str
    name: str

class VoteInput(BaseModel):
    voter_id: str
    candidate: str

# ---------------------------
# API Routes
# ---------------------------

@app.get("/")
def root():
    return {"message": "Blockchain Voting API is running"}

@app.post("/register")
def register_voter(voter: RegisterVoter, db: Session = Depends(get_db)):
    existing = db.query(Voter).filter(Voter.voter_id == voter.voter_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Voter already registered.")
    new_voter = Voter(voter_id=voter.voter_id, name=voter.name)
    db.add(new_voter)
    db.commit()
    return {"message": "Voter registered successfully", "voter_id": voter.voter_id}

@app.post("/login")
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(Voter).filter(Voter.username == credentials.username).first()
    if not user or not verify_pin(credentials.pin, user.hashed_pin):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Simulated session
    logged_in_users[credentials.username] = True
    return {"message": "Login successful."}

@app.post("/vote")
def vote(vote: VoteInput, db: Session = Depends(get_db)):
    voter = db.query(Voter).filter(Voter.voter_id == vote.voter_id).first()
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not registered.")
    if voter.has_voted:
        raise HTTPException(status_code=400, detail="Voter has already voted.")
    
    blockchain.add_vote(vote.voter_id, vote.candidate)
    voter.has_voted = True
    db.commit()
    return {"message": "Vote cast successfully", "voter_id": vote.voter_id}

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
