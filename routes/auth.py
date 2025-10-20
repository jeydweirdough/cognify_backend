from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from core.security import create_access_token, create_refresh_token, get_password_hash
from models.user_models import User, SignUpSchema
from utils.firebase_utils import get_user_by_email, create_user_with_email_and_password
from database.firestore import db
import uuid
from core.firebase import auth
from core.config import settings
from models.user_models import UserProfileModel
from utils.firebase_utils import create_profile_for_uid
import requests
from fastapi.responses import JSONResponse
from fastapi import Request

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
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    try:
        user = auth.sign_in_with_email_and_password(email, password)
        access_token = create_access_token(data={"sub": user['localId']})
        refresh_token = create_refresh_token(data={"sub": user['localId']})

        # --- MODIFIED: Use dynamic cookie settings ---
        response.set_cookie(
            key="refresh_token", 
            value=refresh_token, 
            httponly=True, 
            samesite=COOKIE_SAMESITE, # 👈 CHANGED
            secure=COOKIE_SECURE       # 👈 CHANGED
        )
        
        return {"token": access_token, "refresh_token": refresh_token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout")
async def logout(response: Response):
    # --- MODIFIED: Must MATCH set_cookie parameters EXACTLY ---
    response.delete_cookie(
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