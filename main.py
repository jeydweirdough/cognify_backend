# main.py
import json
import os
import requests
import uvicorn
from typing import Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.sessions import SessionMiddleware

import firebase_admin
from firebase_admin import credentials, auth, firestore

from dotenv import load_dotenv

from models import SignUpSchema, LoginSchema, UserProfileModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from firebase_admin import auth as firebase_auth

load_dotenv()

app = FastAPI(
    description="Cognify backend API",
    title="Cognify API",
    docs_url="/"
)

origins = [
    "http://localhost:5173",  # Vite default dev server
    "http://localhost:3000",  # Alternative port
    "https://cognify-admins.vercel.app",  # Production domain
    "http://localhost:8000",
]

# Add SessionMiddleware first
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "super-secret-session-key"),
)

# Then add CORS middleware separately
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
# Verify Firebase ID Token
# -------------------------
def verify_firebase_token(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        token = auth_header.split(" ")[1]
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

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
    try:
        creds = firebase_login_with_email(user_data.email, user_data.password)
        uid = creds.get("localId")

        # Fetch user profile
        profile_doc = None
        if uid:
            doc_snap = db.collection("user_profiles").document(uid).get()
            if doc_snap.exists:
                profile_doc = doc_snap.to_dict()
                profile_doc["id"] = doc_snap.id

        # Build the JSONResponse with tokens in body
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

        # Set refresh token as HTTP-only cookie (backup)
        resp.set_cookie(
            key="refresh_token",
            value=creds["refreshToken"],
            httponly=True,
            secure=False,  # True only when using HTTPS
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        return resp

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/logout")
async def logout_page(request: Request):
    # Clear the refresh token cookie
    response = JSONResponse(content={"message": "Logged out successfully"}, status_code=200)
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return response


@app.post("/refresh")
async def refresh_token(request: Request):
    """
    Refresh Firebase ID token using the stored refresh_token (from cookie or body).
    Returns the same response format as /login for frontend consistency.
    """
    body = await request.json() if request.method == "POST" else {}
    refresh_tok = body.get("refresh_token") or request.cookies.get("refresh_token")

    if not refresh_tok:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        # Exchange refresh token for new ID token
        url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
        data = {"grant_type": "refresh_token", "refresh_token": refresh_tok}
        res = requests.post(url, data=data, timeout=10)

        if res.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid or expired refresh token")

        payload = res.json()

        new_refresh = payload.get("refresh_token") or payload.get("refreshToken")
        new_id_token = payload.get("id_token") or payload.get("idToken")
        user_id = payload.get("user_id") or payload.get("userId")

        # Retrieve user's profile (so frontend gets full data again)
        profile_doc = None
        if user_id:
            doc_snap = db.collection("user_profiles").document(user_id).get()
            if doc_snap.exists:
                profile_doc = doc_snap.to_dict()
                profile_doc["id"] = doc_snap.id

        response = JSONResponse(
            content={
                "token": new_id_token,
                "refresh_token": new_refresh,
                "email": payload.get("user_id"),
                "uid": user_id,
                "profile": profile_doc,
                "message": "Token refreshed successfully",
            },
            status_code=200,
        )

        # Refresh the cookie with the new refresh token
        if new_refresh:
            response.set_cookie(
                key="refresh_token",
                value=new_refresh,
                httponly=True,
                secure=False,  # Change to True in production (HTTPS)
                samesite="lax",  # Change to "none" if cross-site
                max_age=60 * 60 * 24 * 7,
            )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


# -------------------------
# User Profile router (CRUD)
# -------------------------
router = APIRouter(prefix="/profiles", tags=["User Profiles"])

def build_login_like_response(uid: str, email: str, token: str, refresh_token: str, profile: dict, message: str):
    """
    Helper to return the same structure as the login response.
    """
    return {
        "token": token,
        "refresh_token": refresh_token,
        "email": email,
        "uid": uid,
        "profile": profile,
        "message": message,
    }
# Get all user profiles (no auth = admin, for testing)
# -------------------------
@router.get("/all", response_model=list[dict])
def get_all_profiles():
    try:
        users_ref = db.collection("user_profiles")
        docs = users_ref.stream()
        all_profiles = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            all_profiles.append(data)
        return all_profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")
    
    
# Get user profile
@router.get("/{user_id}", response_model=dict)
def get_profile(user_id: str, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    email = decoded_token.get("email", None)
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = doc.to_dict()
    profile_data["id"] = user_id

    token = decoded_token.get("token", "")
    refresh_token = decoded_token.get("refresh_token", "")

    return build_login_like_response(uid, email, token, refresh_token, profile_data, "Profile fetched successfully")


# Create user profile
@router.post("/{user_id}", response_model=dict)
def create_profile(user_id: str, payload: UserProfileModel, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    email = decoded_token.get("email", None)
    token = decoded_token.get("token", "")
    refresh_token = decoded_token.get("refresh_token", "")

    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only create your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    if doc_ref.get().exists:
        raise HTTPException(status_code=409, detail="Profile already exists for this user")

    payload.id = user_id
    payload.user_id = user_id
    data = payload.to_dict()
    data["deleted"] = False
    data["updated_at"] = datetime.utcnow().isoformat()
    doc_ref.set(data)

    return build_login_like_response(uid, email, token, refresh_token, data, "Profile created successfully")


@router.put("/{user_id}", response_model=dict)
def update_profile(user_id: str, update_data: dict, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    email = decoded_token.get("email", None)
    token = decoded_token.get("token", "")
    refresh_token = decoded_token.get("refresh_token", "")

    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Remove fields not meant to be updated
    update_data.pop("user_id", None)
    update_data.pop("id", None)
    update_data["updated_at"] = datetime.utcnow().isoformat()

    # 🔹 If the user wants to change email, update Firebase Auth record
    if "email" in update_data and update_data["email"] and update_data["email"] != email:
        try:
            firebase_auth.update_user(uid, email=update_data["email"])
            email = update_data["email"]  # keep the new email for the response
        except firebase_auth.AuthError as e:
            raise HTTPException(status_code=400, detail=f"Failed to update email: {str(e)}")

    # 🔹 Update Firestore profile data
    doc_ref.update(update_data)

    # 🔹 Fetch updated Firestore profile
    updated_profile = doc_ref.get().to_dict()
    updated_profile["id"] = user_id

    return build_login_like_response(uid, email, token, refresh_token, updated_profile, "Profile updated successfully")


# Delete user profile (soft delete)
@router.delete("/{user_id}", response_model=dict)
def delete_profile(user_id: str, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    email = decoded_token.get("email", None)
    token = decoded_token.get("token", "")
    refresh_token = decoded_token.get("refresh_token", "")

    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    doc_ref.update({
        "deleted": True,
        "updated_at": datetime.utcnow().isoformat()
    })

    deleted_profile = doc_ref.get().to_dict()
    deleted_profile["id"] = user_id

    return build_login_like_response(uid, email, token, refresh_token, deleted_profile, "Profile deleted successfully")


app.include_router(router)


# Root
@app.get("/")
def root():
    return {"message": "Cognify API running 🚀"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", port=int(os.getenv("PORT", 8000)), reload=True)