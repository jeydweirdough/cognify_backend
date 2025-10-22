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
        "https://cognify.vercel.app",  # Frontend production URL
        "wss://cognify-backend.vercel.app",
        # Allow all subdomains of vercel.app for preview deployments
        "https://*.vercel.app"
    ]

    # WebSocket specific settings
    WS_PING_INTERVAL = 30  # Send ping every 30 seconds
    WS_PING_TIMEOUT = 10   # Wait 10 seconds for pong response
    WS_CLOSE_TIMEOUT = 5   # Wait 5 seconds for graceful closure

settings = Settings()
