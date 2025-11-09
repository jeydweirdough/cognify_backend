# routes/auth.py
import asyncio
from fastapi import APIRouter, HTTPException, Request, status, Depends # <-- Add Depends
from fastapi.responses import JSONResponse
from firebase_admin import auth
import requests

from database.models import (
    SignUpSchema, 
    LoginSchema, 
    UserProfileBase
)
from services import profile_service
from services.role_service import get_role_id_by_designation

from utils.firebase_utils import firebase_login_with_email
from core.config import settings
from core.firebase import db
# --- 1. Import security and the new status util ---
from core.security import verify_firebase_token
from utils.status_utils import update_user_status 
from google.cloud.firestore_v1.base_query import FieldFilter

COOKIE_SAMESITE = "lax"
COOKIE_SECURE = False
if settings.ENVIRONMENT == "production":
    COOKIE_SAMESITE = "none"
    COOKIE_SECURE = True
# ... (rest of cookie config is unchanged) ...

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_page(auth_data: SignUpSchema):
    # ... (this function is unchanged) ...
    
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        raise HTTPException(
            status_code=500, 
            detail="System configuration error: 'student' role not found."
        )

    # 1. Create Firebase Auth user first
    try:
        fb_user = auth.create_user(
            email=auth_data.email, 
            password=auth_data.password
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {auth_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. If Auth user succeeds, create the Firestore profile
    try:
        profile_payload = UserProfileBase(
            email=fb_user.email,
            role_id=student_role_id,
        )
        
        await profile_service.create(profile_payload, doc_id=fb_user.uid)
        
        # --- 2. ADDED: Set status to "online" on signup ---
        await update_user_status(fb_user.uid, "online")
        
        return JSONResponse(
            content={"message": "Successfully created user", "uid": fb_user.uid, "email": fb_user.email},
            status_code=201,
        )
    except Exception as e:
        # --- ROLLBACK ---
        try:
            auth.delete_user(fb_user.uid)
        except Exception as rollback_e:
            raise HTTPException(status_code=500, detail=f"CRITICAL: Profile creation failed, AND auth user rollback failed. {rollback_e}")
        raise HTTPException(status_code=400, detail=f"Failed to create profile: {e}")


@router.post("/login")
async def login_page(user_data: LoginSchema):
    """
    Handles login for ALL users.
    Returns a REAL Firebase ID Token and Refresh Token.
    """
    try:
        creds = firebase_login_with_email(user_data.email, user_data.password)
        uid = creds.get("localId")
        if not uid:
            raise HTTPException(status_code=400, detail="Login failed, no UID returned.")

        # ... (deleted check is unchanged) ...
        doc_snap = db.collection("user_profiles").document(uid).get()
        if doc_snap.exists and doc_snap.to_dict().get("deleted"):
            raise HTTPException(status_code=403, detail="User profile is deleted.")
        
        id_token = creds.get("idToken")
        refresh_token = creds.get("refreshToken")

        if not id_token:
            raise HTTPException(status_code=400, detail="Login failed, no ID Token returned.")

        # --- 3. ADDED: Set status to "online" on login ---
        await update_user_status(uid, "online")

        resp = JSONResponse(
            content={
                "token": id_token, 
                "refresh_token": refresh_token, 
                "message": "Login successful"
            },
            status_code=200,
        )
        resp.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax")
        return resp
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail="Invalid email or password.")


@router.post("/logout")
async def logout_page(
    request: Request,
    # --- 4. ADDED: Make this an authenticated endpoint to get UID ---
    decoded: dict = Depends(verify_firebase_token) 
):
    uid = decoded.get("uid")
    if uid:
        # --- 5. ADDED: Set status to "offline" on logout ---
        # We don't await this, let it run in the background
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
    # ... (this function is unchanged) ...
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