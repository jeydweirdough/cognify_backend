from fastapi import APIRouter, HTTPException, Request, Depends, Body
from datetime import datetime
from firebase_admin import auth as firebase_auth
from database.firestore import db
from core.security import allowed_users
import asyncio
from typing import Dict, Any, Optional

router = APIRouter(prefix="/profiles", tags=["User Profiles"])


def build_login_like_response(uid: str, email: Optional[str], token: str, refresh_token: str, profile: Dict[str, Any], message: str):
    """Keep consistent response format."""
    data = {"email": email, "uid": uid, "profile": profile, "message": message}
    if token and refresh_token:
        data.update({"token": token, "refresh_token": refresh_token})
    return data


def _get_auth_email(uid: str) -> Optional[str]:
    """Fetch the Firebase-auth email for a given uid."""
    try:
        return firebase_auth.get_user(uid).email
    except Exception:
        return None


@router.get("/all")
async def get_all_profiles(request: Request, decoded=Depends(allowed_users(["admin"]))):
    """Admin: view all profiles, ensuring the email matches Firebase."""
    if decoded.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view all profiles.")

    def _fetch_profiles():
        users_ref = db.collection("user_profiles")
        profiles = []
        for doc in users_ref.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            auth_email = _get_auth_email(doc.id)
            if auth_email:
                data["email"] = auth_email  # ensure Firestore and Auth are in sync
            profiles.append(data)
        return profiles

    profiles = await asyncio.to_thread(_fetch_profiles)
    return profiles


@router.post("/", status_code=201)
async def create_profile(
    request: Request,
    profile_data: Dict[str, Any] = Body(...),
    decoded=Depends(allowed_users(["admin", "student"]))
):
    """Create a user profile with the email taken from Firebase Auth."""
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    if not profile_data.get("user_id"):
        profile_data["user_id"] = caller_uid

    if caller_role != "admin" and profile_data["user_id"] != caller_uid:
        raise HTTPException(status_code=403, detail="Students can only create their own profile.")

    uid = profile_data["user_id"]

    def _create_doc():
        col = db.collection("user_profiles")
        doc_ref = col.document(uid)
        if doc_ref.get().exists:
            raise HTTPException(status_code=409, detail="Profile already exists")

        now = datetime.utcnow().isoformat()
        profile_data["created_at"] = now
        profile_data["updated_at"] = now
        profile_data.setdefault("deleted", False)

        # Always get email from Firebase Auth
        auth_email = _get_auth_email(uid)
        if not auth_email:
            raise HTTPException(status_code=404, detail="Firebase user not found.")
        profile_data["email"] = auth_email

        doc_ref.set(profile_data)
        saved = doc_ref.get().to_dict()
        saved["id"] = uid
        return saved

    created = await asyncio.to_thread(_create_doc)
    return build_login_like_response(decoded["uid"], decoded.get("email"), "", "", created, "Profile created successfully")


@router.get("/{user_id}")
async def get_profile(user_id: str, request: Request, decoded=Depends(allowed_users(["admin", "student"]))):
    """User: view own profile, Admin: can view any profile."""
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    if caller_role != "admin" and user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You may only view your own profile.")

    def _get_doc():
        doc = db.collection("user_profiles").document(user_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")

        data = doc.to_dict()
        data["id"] = user_id

        # Always refresh email from Firebase
        auth_email = _get_auth_email(user_id)
        if auth_email:
            data["email"] = auth_email
        return data

    profile = await asyncio.to_thread(_get_doc)
    return build_login_like_response(caller_uid, decoded.get("email"), "", "", profile, "Profile fetched successfully")


@router.put("/{user_id}")
async def update_profile(
    user_id: str,
    update_data: Dict[str, Any] = Body(...),
    decoded=Depends(allowed_users(["admin", "student"]))
):
    """User: update own profile, Admin: can update any. Also syncs Firebase Auth email."""
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    if caller_role != "admin" and user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You may only update your own profile.")

    def _update_doc():
        doc_ref = db.collection("user_profiles").document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Profile not found")

        # If email is being updated, update Firebase Auth too
        if "email" in update_data:
            try:
                firebase_auth.update_user(user_id, email=update_data["email"])
            except firebase_auth.UserNotFoundError:
                raise HTTPException(status_code=404, detail="Firebase user not found.")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to update Firebase email: {e}")

        update_data["updated_at"] = datetime.utcnow().isoformat()
        doc_ref.update(update_data)

        updated = doc_ref.get().to_dict()
        updated["id"] = user_id

        # Always ensure Firestore email matches Firebase Auth
        auth_email = _get_auth_email(user_id)
        if auth_email:
            updated["email"] = auth_email
            doc_ref.update({"email": auth_email})

        return updated

    updated = await asyncio.to_thread(_update_doc)
    return build_login_like_response(caller_uid, decoded.get("email"), "", "", updated, "Profile updated successfully")


@router.delete("/{user_id}")
async def delete_profile(user_id: str, request: Request, decoded=Depends(allowed_users(["admin"]))):
    """Soft-delete a profile (admin only)."""
    if decoded.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete profiles.")

    def _delete_doc():
        doc_ref = db.collection("user_profiles").document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Profile not found")

        doc_ref.update({
            "deleted": True,
            "updated_at": datetime.utcnow().isoformat()
        })
        deleted = doc_ref.get().to_dict()
        deleted["id"] = user_id

        auth_email = _get_auth_email(user_id)
        if auth_email:
            deleted["email"] = auth_email
        return deleted

    deleted = await asyncio.to_thread(_delete_doc)
    return build_login_like_response(decoded["uid"], decoded.get("email"), "", "", deleted, "Profile deleted successfully")
