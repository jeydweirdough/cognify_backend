# routes/auth.py - REFACTORED (Removed redundant models)
import asyncio
from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from firebase_admin import auth
import requests

# --- IMPORT MODELS FROM database/models.py ---
from database.models import UserProfileBase
from pydantic import BaseModel, EmailStr
from services import profile_service
from services.role_service import get_role_id_by_designation
from utils.firebase_utils import firebase_login_with_email
from core.config import settings
from core.firebase import db
from core.security import verify_firebase_token
from utils.status_utils import update_user_status 
from google.cloud.firestore_v1.base_query import FieldFilter

COOKIE_SAMESITE = "lax"
COOKIE_SECURE = False
if settings.ENVIRONMENT == "production":
    COOKIE_SAMESITE = "none"
    COOKIE_SECURE = True

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- MINIMAL AUTH MODELS (Only for password handling) ---
class LoginSchema(BaseModel):
    """Minimal model for login (password not stored in profile)"""
    email: EmailStr
    password: str

class SignUpSchema(BaseModel):
    """Signup schema - extends profile fields with password"""
    email: EmailStr
    password: str
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    nickname: str | None = None
    user_name: str | None = None
    profile_picture: str | None = None
    image: str | None = None

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_page(auth_data: SignUpSchema):
    """[Public] Register a new student account"""
    
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        raise HTTPException(
            status_code=500, 
            detail="System configuration error: 'student' role not found."
        )

    # 1. Create Firebase Auth user
    try:
        fb_user = auth.create_user(
            email=auth_data.email, 
            password=auth_data.password
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400, 
            detail=f"Account with email {auth_data.email} already exists."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Create Firestore profile using UserProfileBase
    try:
        profile_payload = UserProfileBase(
            email=fb_user.email,
            role_id=student_role_id,
            first_name=auth_data.first_name,
            middle_name=auth_data.middle_name,
            last_name=auth_data.last_name,
            nickname=auth_data.nickname,
            user_name=auth_data.user_name,
            profile_picture=auth_data.profile_picture or auth_data.image,
            image=auth_data.image or auth_data.profile_picture
        )
        
        await profile_service.create(profile_payload, doc_id=fb_user.uid)
        
        # Set status to online
        await update_user_status(fb_user.uid, "online")
        
        return JSONResponse(
            content={
                "message": "Successfully created user", 
                "uid": fb_user.uid, 
                "email": fb_user.email
            },
            status_code=201,
        )
    except Exception as e:
        # Rollback: Delete auth user if profile creation fails
        try:
            auth.delete_user(fb_user.uid)
        except Exception as rollback_e:
            raise HTTPException(
                status_code=500, 
                detail=f"CRITICAL: Profile creation failed, AND auth rollback failed. {rollback_e}"
            )
        raise HTTPException(status_code=400, detail=f"Failed to create profile: {e}")

@router.post("/login")
async def login_page(user_data: LoginSchema):
    """[Public] Login for all users (student, faculty, admin)"""
    try:
        creds = firebase_login_with_email(user_data.email, user_data.password)
        uid = creds.get("localId")
        if not uid:
            raise HTTPException(status_code=400, detail="Login failed, no UID returned.")

        # Check if user profile is deleted
        doc_snap = db.collection("user_profiles").document(uid).get()
        if doc_snap.exists and doc_snap.to_dict().get("deleted"):
            raise HTTPException(status_code=403, detail="User profile is deleted.")
        
        id_token = creds.get("idToken")
        refresh_token = creds.get("refreshToken")

        if not id_token:
            raise HTTPException(status_code=400, detail="Login failed, no ID Token returned.")

        # Set status to online
        await update_user_status(uid, "online")

        resp = JSONResponse(
            content={
                "token": id_token, 
                "refresh_token": refresh_token, 
                "message": "Login successful"
            },
            status_code=200,
        )
        resp.set_cookie(
            key="refresh_token", 
            value=refresh_token, 
            httponly=True, 
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE
        )
        return resp
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail="Invalid email or password.")

@router.post("/logout")
async def logout_page(
    request: Request,
    decoded: dict = Depends(verify_firebase_token) 
):
    """[Authenticated] Logout user"""
    uid = decoded.get("uid")
    if uid:
        # Set status to offline (background task)
        asyncio.create_task(update_user_status(uid, "offline"))

    response = JSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(
        key="refresh_token", 
        httponly=True, 
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE
    )
    return response

@router.post("/refresh")
async def refresh_token(request: Request):
    """[Public] Refresh expired ID token"""
    body = await request.json()
    refresh_tok = body.get("refresh_token") or request.cookies.get("refresh_token")
    if not refresh_tok:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    
    url = f"https://securetoken.googleapis.com/v1/token?key={settings.FIREBASE_API_KEY}"
    data = {"grant_type": "refresh_token", "refresh_token": refresh_tok}
    res = requests.post(url, data=data, timeout=10)
    
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    new_creds = res.json()
    
    return {
        "token": new_creds.get("id_token"),
        "refresh_token": new_creds.get("refresh_token"),
        "message": "Token refreshed successfully",
    }