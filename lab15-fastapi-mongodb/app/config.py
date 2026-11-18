"""Central configuration - everything can be overridden with environment variables."""
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("DB_NAME", "tasktracker")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "lab15-dev-secret-change-me-0123456789abcdef")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Rate limiting (fixed window counter stored in MongoDB)
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))                  # requests per window / user
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))    # window length (s)
LOGIN_RATE_LIMIT_MAX = int(os.getenv("LOGIN_RATE_LIMIT_MAX", "30"))      # login/signup per window / IP

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
