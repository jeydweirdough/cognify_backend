import requests
from fastapi import HTTPException
from app.core.config import settings
from app.database.firestore import db
from app.models.user_models import UserProfileModel

def firebase_login_with_email(email: str, password: str):
    if not settings.FIREBASE_API_KEY:
        raise RuntimeError("FIREBASE_API_KEY not set")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    if resp.status_code != 200:
        msg = data.get("error", {}).get("message", "Login failed")
        raise HTTPException(status_code=400, detail=msg)
    return data

def create_profile_for_uid(uid: str, signup: UserProfileModel):
    profile = UserProfileModel(
        id=uid,
        user_id=uid,
        first_name=signup.first_name,
        middle_name=signup.middle_name,
        last_name=signup.last_name,
        nickname=signup.nickname,
        role_id=signup.role_id,
    )
    db.collection("user_profiles").document(uid).set(profile.to_dict())
    return profile
