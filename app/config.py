import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genie.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-secret-key-min-32-chars!!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
