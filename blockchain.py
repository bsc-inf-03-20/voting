import hashlib
import json
from time import time

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.difficulty = 4  # Number of leading zeros required
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = self.create_block(previous_hash='0')
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
            'votes': self.current_votes,
            'previous_hash': previous_hash,
            'nonce': 0,
            'hash': ''  # Will be set by proof_of_work
        }
        block['hash'] = self.proof_of_work(block)
        self.current_votes = []
        return block

    def add_vote(self, voter_id, username, candidate):
        if not isinstance(voter_id, str) or not isinstance(username, str) or not isinstance(candidate, str):
            raise ValueError("Invalid vote data types")
        vote = {
            'voter_id': voter_id,
            'username': username,
            'candidate': candidate,
            'timestamp': time()
        }
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