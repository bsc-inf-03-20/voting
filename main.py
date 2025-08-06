from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import hashlib
import json
from time import time

app = FastAPI()

# --------------------------
# Blockchain Voting System
# --------------------------

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.voted_ids = set()  # Prevent double voting
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
        if voter_id in self.voted_ids:
            return False  # Voter already voted
        vote = {'voter_id': voter_id, 'candidate': candidate}
        self.current_votes.append(vote)
        self.voted_ids.add(voter_id)
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

# --------------------------
# Initialize Blockchain
# --------------------------

blockchain = Blockchain()

# --------------------------
# API Models
# --------------------------

class VoteInput(BaseModel):
    voter_id: str
    candidate: str

# --------------------------
# API Routes
# --------------------------

@app.get("/")
def root():
    return {"message": "Blockchain Voting API is running"}

@app.post("/vote")
def vote(vote: VoteInput):
    result = blockchain.add_vote(vote.voter_id, vote.candidate)
    if not result:
        raise HTTPException(status_code=400, detail="Voter has already voted.")
    return {"message": "Vote added successfully", "vote": result}

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
