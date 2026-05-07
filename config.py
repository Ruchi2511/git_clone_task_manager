import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    MONGO_URI = os.getenv("MONGO_URI")

    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    SESSION_COOKIE_SECURE = FLASK_ENV == "production"