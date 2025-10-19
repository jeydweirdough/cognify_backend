from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from firebase_admin import auth as firebase_auth

from app.database.firestore import db
from app.core.security import verify_firebase_token
from app.models.user_models import UserProfileModel

router = APIRouter(prefix="/profiles", tags=["User Profiles"])

def build_login_like_response(uid, email, token, refresh_token, profile, message):
    return {
        "token": token,
        "refresh_token": refresh_token,
        "email": email,
        "uid": uid,
        "profile": profile,
        "message": message,
    }

@router.get("/{user_id}")
def get_profile(user_id: str, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = doc.to_dict()
    profile_data["id"] = user_id
    return build_login_like_response(uid, decoded_token.get("email"), "", "", profile_data, "Profile fetched successfully")

@router.put("/{user_id}")
def update_profile(user_id: str, update_data: dict, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data["updated_at"] = datetime.utcnow().isoformat()

    if "email" in update_data and update_data["email"] != decoded_token.get("email"):
        firebase_auth.update_user(uid, email=update_data["email"])

    doc_ref.update(update_data)
    updated_profile = doc_ref.get().to_dict()
    updated_profile["id"] = user_id
    return build_login_like_response(uid, decoded_token.get("email"), "", "", updated_profile, "Profile updated successfully")

@router.delete("/{user_id}")
def delete_profile(user_id: str, decoded_token: dict = Depends(verify_firebase_token)):
    uid = decoded_token["uid"]
    if uid != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own profile")

    doc_ref = db.collection("user_profiles").document(user_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    doc_ref.update({"deleted": True, "updated_at": datetime.utcnow().isoformat()})
    deleted_profile = doc_ref.get().to_dict()
    deleted_profile["id"] = user_id
    return build_login_like_response(uid, decoded_token.get("email"), "", "", deleted_profile, "Profile deleted successfully")
