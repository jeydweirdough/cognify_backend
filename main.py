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

# Import your updated models.py (SignUpSchema includes profile fields)
from models import SignUpSchema, LoginSchema, UserProfileModel
from fastapi.middleware.cors import CORSMiddleware

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

        # Build the JSONResponse FIRST
        resp = JSONResponse(
            content={
                "token": creds["idToken"],
                "email": creds["email"],
                "uid": uid,
                "profile": profile_doc,
                "message": "Login successful",
            },
            status_code=200,
        )

        # Then attach cookie directly to it
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
async def logout_page(request: Request, response: Response):
    # Try to read the refresh token cookie
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token cookie found")

    # Clear the refresh cookie from the client
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("refresh_token")

    return response


@app.post("/refresh")
async def refresh_token(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token cookie")

    try:
        url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        res = requests.post(url, data=data, timeout=10)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        payload = res.json()

        # Firebase returns a new refresh_token
        new_refresh = payload.get("refresh_token") or payload.get("refreshToken")
        new_id_token = payload.get("id_token") or payload.get("idToken")

        # Update cookie if Firebase issued a new one
        if new_refresh:
            response.set_cookie(
                key="refresh_token",
                value=new_refresh,
                httponly=True,
                secure=False,  # Set True in production
                samesite="lax",
                max_age=60 * 60 * 24 * 7,
            )

        return JSONResponse(
            content={"token": new_id_token, "message": "Token refreshed"},
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


# -------------------------
# User Profile router (CRUD)
# -------------------------
router = APIRouter(prefix="/profiles", tags=["User Profiles"])

# -------------------------
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
    

@router.get("/{user_id}", response_model=UserProfileModel)
def get_profile(user_id: str, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")

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
def update_profile(
    user_id: str,
    update_data: dict,
    decoded_token: dict = Depends(verify_firebase_token),
):
    uid = decoded_token["uid"]
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Prevent ID tampering
    update_data.pop("user_id", None)
    update_data.pop("id", None)

    doc_ref.update(update_data)
    return {"message": "Profile updated successfully"}


@router.delete("/{user_id}", response_model=dict)
def delete_profile(
    user_id: str,
    decoded_token: dict = Depends(verify_firebase_token),
):
    uid = decoded_token["uid"]
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own profile")

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
    uvicorn.run(app="main:app", port=int(os.getenv("PORT", 8000)), reload=True)