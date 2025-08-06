import hashlib

def hash_pin(pin: str):
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin: str, hashed: str):
    return hash_pin(pin) == hashed
