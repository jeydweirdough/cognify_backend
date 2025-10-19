from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from firebase_admin import auth
import requests

from app.models.user_models import SignUpSchema, LoginSchema
from app.utils.firebase_utils import firebase_login_with_email, create_profile_for_uid
from app.core.config import settings
from app.database.firestore import db

router = APIRouter(tags=["Authentication"])

@router.post("/signup")
async def signup_page(user_data: SignUpSchema):
    try:
        fb_user = auth.create_user(email=user_data.email, password=user_data.password)
        profile = create_profile_for_uid(fb_user.uid, user_data)
        return JSONResponse(
            content={"message": "Successfully created user", "uid": fb_user.uid, "profile": profile.to_dict()},
            status_code=201,
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {user_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login_page(user_data: LoginSchema):
    try:
        creds = firebase_login_with_email(user_data.email, user_data.password)
        uid = creds.get("localId")

        profile_doc = None
        if uid:
            doc_snap = db.collection("user_profiles").document(uid).get()
            if doc_snap.exists:
                profile_doc = doc_snap.to_dict()
                profile_doc["id"] = doc_snap.id

        resp = JSONResponse(
            content={
                "token": creds["idToken"],
                "refresh_token": creds["refreshToken"],
                "email": creds["email"],
                "uid": uid,
                "profile": profile_doc,
                "message": "Login successful",
            },
            status_code=200,
        )
        resp.set_cookie(key="refresh_token", value=creds["refreshToken"], httponly=True, samesite="lax")
        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
async def logout_page(request: Request):
    response = JSONResponse(content={"message": "Logged out successfully"}, status_code=200)
    response.delete_cookie("refresh_token", path="/", httponly=True, samesite="lax")
    return response

@router.post("/refresh")
async def refresh_token(request: Request):
    body = await request.json()
    refresh_tok = body.get("refresh_token") or request.cookies.get("refresh_token")
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
