import hashlib
import json
from time import time

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.difficulty = 4
        self.create_genesis_block()
    
    def create_genesis_block(self):
        genesis_block = {
            'index': 1,
            'timestamp': time(),
            'votes': [],
            'previous_hash': '0',
            'nonce': 0
        }
        genesis_block['hash'] = self.proof_of_work(genesis_block)
        self.chain.append(genesis_block)

    def proof_of_work(self, block):
        block_copy = block.copy()
        block_copy.pop('hash', None)
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        
        nonce = 0
        while True:
            hash_attempt = hashlib.sha256(block_string + str(nonce).encode()).hexdigest()
            if hash_attempt.startswith('0' * self.difficulty):
                return hash_attempt
            nonce += 1

    def create_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'votes': self.current_votes.copy(),  # Important: use copy()
            'previous_hash': previous_hash,
            'nonce': 0,
            'hash': ''
        }
        block['hash'] = self.proof_of_work(block)
        self.chain.append(block)
        self.current_votes = []  # Clear current votes after mining
        return block

    def add_vote(self, member_id, username, candidate):
        if not all(isinstance(x, str) for x in [member_id, username, candidate]):
            raise ValueError("All vote parameters must be strings")
            
        # Debug print to verify votes are being added
        print(f"Adding vote: {member_id}, {username}, {candidate}")
        vote = {
            'member_id': member_id,
            'username': username,
            'candidate': candidate,
            'timestamp': time()
        }
        self.current_votes.append(vote)
        return vote

    def mine_pending_votes(self):
        if not self.current_votes:
            print("Warning: No votes to mine!")
            return None
    
        # Debug print to show votes being mined
        print(f"Mining {len(self.current_votes)} votes")
        
        last_block = self.get_last_block()
        new_block = self.create_block(last_block['hash'])
        
        # Debug print to verify block contents
        print(f"New block contains {len(new_block['votes'])} votes")
        
        return new_block

    def count_votes(self):
        tally = {}
        # Count votes in all blocks except genesis (which has no votes)
        for block in self.chain[1:]:
            for vote in block['votes']:
                candidate = vote['candidate']
                tally[candidate] = tally.get(candidate, 0) + 1
        return tally

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def hash_block(self, block):
        block_copy = block.copy()
        block_copy.pop('hash', None)
        return hashlib.sha256(json.dumps(block_copy, sort_keys=True).encode()).hexdigest()