from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from firebase_admin import auth
import requests

from models.user_models import SignUpSchema, LoginSchema, UserProfileModel
from utils.firebase_utils import firebase_login_with_email, create_profile_for_uid
from core.config import settings
from database.firestore import db
# 1. --- IMPORT get_user_role ---
from core.security import get_user_role

COOKIE_SAMESITE = "lax"
COOKIE_SECURE = False

if settings.ENVIRONMENT == "production":
    COOKIE_SAMESITE = "none"
    COOKIE_SECURE = True

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup")
async def signup_page(auth_data: SignUpSchema):
    profile_data = UserProfileModel(
        id="",
        user_id="",
        email=auth_data.email,
        first_name="",
        middle_name="",
        last_name="",
        nickname="",
        role_id="Tzc78QtZcaVbzFtpHoOL", # only students has the default role for sign up
    )

    try:
        fb_user = auth.create_user(email=auth_data.email, password=auth_data.password)
        
        create_profile_for_uid(fb_user.uid, profile_data)
        
        return JSONResponse(
            content={"message": "Successfully created user", "uid": fb_user.uid, "email": fb_user.email},
            status_code=201,
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {auth_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login_page(user_data: LoginSchema):
    try:
        creds = firebase_login_with_email(user_data.email, user_data.password)
        uid = creds.get("localId")

        profile_doc = None
        role = "student"  # Default role

        if uid:
            # 2. --- FETCH PROFILE AND ROLE ---
            try:
                # Use the function from security.py
                role = await get_user_role(uid) 
                
                doc_snap = db.collection("user_profiles").document(uid).get()
                if doc_snap.exists:
                    profile_doc = doc_snap.to_dict()
                    profile_doc["id"] = doc_snap.id

                    if doc_snap.to_dict().get("deleted"):
                        raise HTTPException(status_code=403, detail="User profile is deleted.")
                    
            except HTTPException as e:
                print(f"Profile/role fetch failed for {uid}: {e.detail}")
                # This handles users in Auth but not in profiles
                if "not found" in str(e.detail).lower():
                    # Default to 'student' if profile/role is missing
                    role = "student" 
                else:
                    raise e  # Re-raise other errors
            # --- END OF MODIFICATION ---

        resp = JSONResponse(
            content={
                "token": creds["idToken"],
                "refresh_token": creds["refreshToken"],
                # --- END OF MODIFICATION ---
                "message": "Login successful",
            },
            status_code=200,
        )
        # This cookie is fine, but the frontend will also save one
        resp.set_cookie(key="refresh_token", value=creds["refreshToken"], httponly=True, samesite="lax")
        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
async def logout_page(request: Request):
    # --- MODIFIED: Must MATCH set_cookie parameters EXACTLY ---
    request.delete_cookie(
        key="refresh_token", 
        httponly=True, 
        samesite=COOKIE_SAMESITE, # 👈 CHANGED
        secure=COOKIE_SECURE       # 👈 CHANGED
    )
    return {"message": "Logout successful"}

@router.post("/refresh")
async def refresh_token(request: Request):
    body = await request.json()
    refresh_tok = body.get("refresh_token") or request.cookies.get("refresh_token")
    print(refresh_tok)
    if not refresh_tok:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    url = f"https://securetoken.googleapis.com/v1/token?key={settings.FIREBASE_API_KEY}"
    data = {"grant_type": "refresh_token", "refresh_token": refresh_tok}
    res = requests.post(url, data=data, timeout=10)

    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid or expired refresh token")

    payload = res.json()
    return {
        "token": payload.get("id_token"),
        "refresh_token": payload.get("refresh_token"),
        "message": "Token refreshed successfully",
    }