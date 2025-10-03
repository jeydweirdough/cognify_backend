# main.py
import json
import os
import requests
import uvicorn
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

import firebase_admin
from firebase_admin import credentials, auth, firestore

from dotenv import load_dotenv

# Import your updated models.py (SignUpSchema includes profile fields)
from models import SignUpSchema, LoginSchema, UserProfileModel

load_dotenv()

app = FastAPI(
    description="Cognify backend API",
    title="Cognify API",
    docs_url="/"
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "change-this-secret"),
    session_cookie="cognify_session",
    max_age=1800,
    same_site="lax",
    https_only=False  # set True in production
)

# -------------------------
# Firebase Admin + Firestore
# -------------------------
if not firebase_admin._apps:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
    else:
        # local fallback - keep this file out of git!
        cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------
# OAuth setup (Google)
# -------------------------
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# -------------------------
# Firebase REST helpers
# -------------------------
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")


def firebase_login_with_email(email: str, password: str) -> Dict[str, Any]:
    if not FIREBASE_API_KEY:
        raise RuntimeError("FIREBASE_API_KEY not set")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    if resp.status_code != 200:
        msg = data.get("error", {}).get("message", "Login failed")
        raise HTTPException(status_code=400, detail=msg)
    return data


def firebase_login_with_custom_token(custom_token: str) -> Dict[str, Any]:
    if not FIREBASE_API_KEY:
        raise RuntimeError("FIREBASE_API_KEY not set")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
    payload = {"token": custom_token, "returnSecureToken": True}
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    if resp.status_code != 200:
        msg = data.get("error", {}).get("message", "Custom token exchange failed")
        raise HTTPException(status_code=400, detail=msg)
    return data


# -------------------------
# Helper: create profile doc (doc id == uid)
# -------------------------
def create_profile_for_uid(uid: str, signup: SignUpSchema) -> UserProfileModel:
    profile = UserProfileModel(
        id=uid,
        user_id=uid,
        first_name=signup.first_name,
        middle_name=signup.middle_name,
        last_name=signup.last_name,
        nickname=signup.nickname,
        role_id=signup.role_id,
    )
    # write doc with id == uid
    db.collection("user_profiles").document(uid).set(profile.to_dict())
    return profile


# -------------------------
# AUTH ROUTES
# -------------------------
@app.post("/signup")
async def signup_page(user_data: SignUpSchema):
    """
    Create Firebase Auth user (email+password) and create a Firestore profile doc (doc id == uid).
    """
    try:
        fb_user = auth.create_user(email=user_data.email, password=user_data.password)
        # create profile using the fields provided
        profile = create_profile_for_uid(fb_user.uid, user_data)
        return JSONResponse(
            content={
                "message": "Successfully created user",
                "uid": fb_user.uid,
                "profile": profile.to_dict(),
            },
            status_code=201,
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {user_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
async def login_page(user_data: LoginSchema):
    """
    Login using Firebase REST API. Return idToken, refreshToken, uid, and profile (if exists).
    (Frontend should handle storing tokens; backend can verify idToken for protected routes.)
    """
    try:
        creds = firebase_login_with_email(user_data.email, user_data.password)
        uid = creds.get("localId")

        # fetch profile doc (doc id == uid)
        profile_doc = None
        if uid:
            doc_snap = db.collection("user_profiles").document(uid).get()
            if doc_snap.exists:
                profile_doc = doc_snap.to_dict()
                profile_doc["id"] = doc_snap.id

        return JSONResponse(
            content={
                "token": creds["idToken"],
                "refreshToken": creds["refreshToken"],
                "uid": uid,
                "profile": profile_doc,
                "message": "Login successful",
            },
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/logout")
async def logout_page(request: Request):
    jwt = request.headers.get("authorization")
    if not jwt:
        raise HTTPException(status_code=401, detail="No authorization token provided")
    try:
        user = auth.verify_id_token(jwt)
        auth.revoke_refresh_tokens(user["uid"])
        return JSONResponse(content={"message": "Successfully logged out. Delete token on client."}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Logout failed: {str(e)}")


@app.post("/refresh")
async def refresh_token(request: Request):
    body = await request.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token provided")
    try:
        url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        res = requests.post(url, data=data, timeout=10)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        return JSONResponse(content=res.json(), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


# -------------------------
# GOOGLE SIGNUP & LOGIN
# -------------------------
@app.get("/signup/google")
async def signup_via_google(request: Request):
    redirect_uri = request.url_for("google_signup_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/signup/google/callback", name="google_signup_callback")
async def google_signup_callback(request: Request):
    """
    Signup with Google: create Auth user and Firestore profile (if not exists).
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info or not user_info.get("email"):
            raise HTTPException(status_code=400, detail="Google account missing email")

        email = user_info["email"]
        name = user_info.get("name")
        picture = user_info.get("picture")

        try:
            # if exists in Firebase, surface error
            auth.get_user_by_email(email)
            raise HTTPException(status_code=400, detail="Account already exists. Please login instead.")
        except auth.UserNotFoundError:
            fb_user = auth.create_user(email=email, display_name=name, photo_url=picture, email_verified=True)
            # create profile doc with same uid
            profile = UserProfileModel(id=fb_user.uid, user_id=fb_user.uid, nickname=name)
            db.collection("user_profiles").document(fb_user.uid).set(profile.to_dict())

        return JSONResponse(content={"message": "Google signup successful", "email": email}, status_code=201)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for("google_login_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/login/google/callback", name="google_login_callback")
async def google_login_callback(request: Request):
    """
    Google login: require pre-existing Firebase user (signup first).
    Exchange custom token and return profile.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info or not user_info.get("email"):
            raise HTTPException(status_code=400, detail="Google account missing email")
        email = user_info["email"]

        try:
            user = auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            raise HTTPException(status_code=403, detail="Account not registered. Please sign up first.")

        custom_token = auth.create_custom_token(user.uid)
        creds = firebase_login_with_custom_token(custom_token.decode())

        # fetch profile
        doc_snap = db.collection("user_profiles").document(user.uid).get()
        profile = doc_snap.to_dict() if doc_snap.exists else None

        return JSONResponse(
            content={
                "token": creds["idToken"],
                "refreshToken": creds.get("refreshToken", ""),
                "uid": user.uid,
                "email": email,
                "profile": profile,
                "message": "Google login successful",
            },
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------
# User Profile router (CRUD)
# -------------------------
router = APIRouter(prefix="/profiles", tags=["User Profiles"])


@router.get("/{user_id}", response_model=UserProfileModel)
def get_profile(user_id: str):
    doc = db.collection("user_profiles").document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserProfileModel.from_dict(doc.to_dict(), doc.id)


@router.post("/{user_id}", response_model=dict)
def create_profile(user_id: str, payload: UserProfileModel):
    """
    Create a profile for an existing UID. Enforces doc id == user_id.
    If profile exists, returns 409 conflict.
    """
    # ensure path param and body user_id match (or body can omit id/user_id)
    if payload.user_id and payload.user_id != user_id:
        raise HTTPException(status_code=400, detail="user_id mismatch between URL and payload")

    doc_ref = db.collection("user_profiles").document(user_id)
    if doc_ref.get().exists:
        raise HTTPException(status_code=409, detail="Profile already exists for this user")

    payload.id = user_id
    payload.user_id = user_id
    doc_ref.set(payload.to_dict())
    return {"id": user_id, "message": "Profile created successfully"}


@router.put("/{user_id}", response_model=dict)
def update_profile(user_id: str, update_data: dict):
    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")
    # do not allow changing user_id or id
    update_data.pop("user_id", None)
    update_data.pop("id", None)
    doc_ref.update(update_data)
    return {"message": "Profile updated successfully"}


@router.delete("/{user_id}", response_model=dict)
def delete_profile(user_id: str):
    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")
    doc_ref.update({"deleted": True})
    return {"message": "Profile soft-deleted successfully"}


app.include_router(router)


# Root
@app.get("/")
def root():
    return {"message": "Cognify API running 🚀"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
