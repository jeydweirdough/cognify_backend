from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from core.config import settings
from routes import (
    auth, profiles, status, activities, assessments, 
    modules, quizzes, recommendations, tos, 
    subjects, analytics, 
    utilities  # --- NEW: Import utilities ---
)

app = FastAPI(
    title="Cognify API",
    description="Cognify backend API",
    docs_url="/"
)

# Middleware setup
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
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

@app.get("/")
def root():
    return {"message": "Cognify API running 🚀"}

if __name__ == "__main__":
    uvicorn.run("main:app", port=settings.PORT, reload=True)
