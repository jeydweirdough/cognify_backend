import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-session-key")
    PORT = int(os.getenv("PORT", 8000))
    ENVIRONMENT = os.getenv("ENVIRONMENT")

    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "https://cognify-backend.vercel.app",
        "https://cognify-admins.vercel.app",
    ]

settings = Settings()
