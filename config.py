import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Firebase Configuration
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")

# App Configuration
APP_DOMAIN = os.getenv("APP_DOMAIN", "http://localhost:8000")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")

# Session Configuration
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "fallback-secret-key")
SESSION_EXPIRES_DAYS = int(os.getenv("SESSION_EXPIRES_DAYS", 5))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")