from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from datetime import timedelta
from typing import Optional
from time import time

from database import SessionLocal, engine
from models import Member  # Changed from Voter to Member
from auth import (
    hash_password, verify_password, is_admin,
    create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, oauth2_scheme
)
from blockchain import Blockchain

# Create DB tables
import models
models.Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
# initialise CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity, adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
blockchain = Blockchain()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic schemas
class RegisterMember(BaseModel):
    full_name: str
    username: str
    password: str
    confirm_password: str

    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        # Add more complexity rules as needed
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError("Passwords don't match")
        return v

class VoteInput(BaseModel):
    candidate: str

class AdminVerification(BaseModel):
    is_verified: bool
    notes: Optional[str] = None

@app.get("/")
def root():
    return {"message": "Blockchain Voting API is running"}
@app.post("/register-admin")
def register_admin(
    admin_data: RegisterMember, 
    db: Session = Depends(get_db)
):
    # In production, protect this endpoint with a super-secret key
    hashed_password = hash_password(admin_data.password)
    
    admin = Member(
        username=admin_data.username,
        hashed_password=hashed_password,
        full_name=admin_data.full_name,
        is_admin=True,  # Mark as admin
        is_verified=True  # Auto-verify admin
    )
    
    db.add(admin)
    db.commit()
    
    return {"message": "Admin account created"}

@app.post("/register")
def register(member: RegisterMember, db: Session = Depends(get_db)):
    existing_member = db.query(Member).filter(Member.username == member.username).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = hash_password(member.password)
    
    new_member = Member(
        full_name=member.full_name,
        username=member.username,
        hashed_password=hashed_password,
        is_verified=False  # Requires admin verification
    )
    
    db.add(new_member)
    db.commit()
    
    return {"message": "Registration submitted for verification", "member_id": new_member.id}

@app.patch("/verify-member/{member_id}")
def verify_member(
    member_id: int,
    verification: AdminVerification,
    current_user: Member = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    member.is_verified = verification.is_verified
    if verification.notes:
        member.verification_notes = verification.notes
    
    db.commit()
    
    return {"message": "Member verification updated"}

@app.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    member = db.query(Member).filter(Member.username == form_data.username).first()
    if not member or not verify_password(form_data.password, member.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not member.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not yet verified by admin"
        )
    
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": member.username},
        expires_delta=token_expires
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": member.username,
        "member_id": member.id
    }

@app.post("/vote")
def vote(
    vote_data: VoteInput,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = db.query(Member).filter(Member.username == current_user).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if not member.is_verified:
        raise HTTPException(status_code=403, detail="Member not verified")
    if member.has_voted:
        raise HTTPException(status_code=400, detail="Already voted")
    
    # Record vote
    blockchain.add_vote(
        member_id=member.id,
        member_name=member.full_name,
        candidate=vote_data.candidate
    )
    
    # Mark as voted
    member.has_voted = True
    db.commit()
    
    return {
        "message": "Vote recorded successfully",
        "details": {
            "candidate": vote_data.candidate,
            "timestamp": time(),
            "pending_confirmation": True
        }
    }

@app.get("/members/me")
def get_profile(
    current_user: str = Depends(get_current_user),
    # db: Session = Depends(get_db)
):
    # member = db.query(Member).filter(Member.username == current_user).first()
    # if not member:
    #     raise HTTPException(status_code=404, detail="Member not found")
    
    return {
        "member_id": current_user.id,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "is_verified": current_user.is_verified,
        "has_voted": current_user.has_voted,
        "join_date": current_user.created_at
    }

@app.post("/mine")
def mine_block(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not blockchain.current_votes:
        raise HTTPException(status_code=400, detail="No votes to mine")
    
    previous_hash = blockchain.get_last_block()["hash"]
    block = blockchain.create_block(previous_hash)
    
    return {
        "message": "Block mined successfully",
        "block_index": block['index'],
        "votes_included": len(block['votes']),
        "block_hash": block['hash']
    }

@app.get("/chain")
def get_chain():
    return {
        "chain_length": len(blockchain.chain),
        "chain": blockchain.chain,
        "pending_votes": len(blockchain.current_votes)
    }

@app.get("/results")
def get_results():
    return {
        "vote_counts": blockchain.count_votes(),
        "total_votes_cast": sum(blockchain.count_votes().values()),
        "last_block_mined": blockchain.get_last_block()['index']
    }