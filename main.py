from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from datetime import datetime
from core.config import settings
from core.firebase import db

# Import all routers
from routes import (
    auth, profiles, status, activities, assessments, 
    modules, quizzes, recommendations, tos, 
    subjects, analytics, utilities, generated_content,
    diagnostics, study_sessions, content_verification
)

app = FastAPI(
    title="Cognify API",
    description="Backend API for Psychology Licensure Exam Preparation System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Cognify Development Team",
        "email": "support@cognify.edu"
    }
)

# Middleware setup
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SESSION_SECRET_KEY
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(status.router)
app.include_router(activities.router)
app.include_router(assessments.router)
app.include_router(modules.router)
app.include_router(quizzes.router)
app.include_router(recommendations.router)
app.include_router(tos.router)
app.include_router(subjects.router)
app.include_router(analytics.router)
app.include_router(utilities.router)
app.include_router(generated_content.router)
app.include_router(diagnostics.router)
app.include_router(study_sessions.router)
app.include_router(content_verification.router)

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": "Cognify API running 🚀",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test Firebase connection
        firebase_status = "connected" if db else "disconnected"
        
        # Check if we can read from Firestore
        try:
            db.collection("roles").limit(1).get()
            firebase_readable = True
        except Exception:
            firebase_readable = False
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "firebase": {
                "status": firebase_status,
                "readable": firebase_readable
            },
            "ai_enabled": bool(settings.GEMINI_API_KEY)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0",
        port=settings.PORT, 
        reload=True
    )