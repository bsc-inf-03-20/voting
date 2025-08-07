# config.py

import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file if present

SECRET_KEY = os.getenv("SECRET_KEY", "blockvotechaning")  # fallback default
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
