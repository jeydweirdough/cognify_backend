from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from firebase_admin import auth as firebase_auth

from database.firestore import db
from core.security import verify_firebase_token
from models.user_models import UserProfileModel

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

# get specific user profile
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

# update specific user profile
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

# delete specific user profile (soft delete)
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

# Get all user profiles (no auth = admin, for testing)
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
