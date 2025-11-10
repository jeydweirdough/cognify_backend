import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Firebase Configuration
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "your-project-name.appspot.com")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    
    # Gemini AI Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Application Configuration
    SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-session-key")
    PORT = int(os.getenv("PORT", 8000))
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Backend URL
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

    # CORS Origins
    ALLOWED_ORIGINS = [
        "http://localhost:5173",  # Web dev
        "http://localhost:3000",  # Alternative web dev
        "http://localhost:8000",  # API docs
        "http://localhost:8081",  # Mobile dev
        "http://localhost:19006", # Expo dev
        "https://cognify-backend.vercel.app",
        "https://cognify-admins.vercel.app",
        "https://cognify.vercel.app",
        "https://*.vercel.app",
    ]
    
    def validate(self):
        """Validate critical configuration"""
        if not self.FIREBASE_API_KEY:
            print("⚠️  WARNING: FIREBASE_API_KEY not set")
        if not self.GEMINI_API_KEY:
            print("⚠️  WARNING: GEMINI_API_KEY not set - AI features will be disabled")
        if not self.FIREBASE_PROJECT_ID:
            print("⚠️  WARNING: FIREBASE_PROJECT_ID not set")

settings = Settings()
settings.validate()