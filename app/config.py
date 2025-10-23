import os

# Defaults for LOCAL DEV. Docker will override via ENV.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "fmp_session")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax")  # "lax" | "strict" | "none"

# Local default uses a file in the repo; Docker will set /data path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mealplanner.db")
