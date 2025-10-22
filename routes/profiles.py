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
    """Admin: view all profiles, ensuring the email matches Firebase and embedding the role designation."""
    if decoded.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view all profiles.")

    def _fetch_profiles_and_roles():
        # 1. Fetch all roles first and store them in a dictionary for quick lookup.
        roles_ref = db.collection("roles")
        roles_map = {doc.id: doc.to_dict().get("designation", "Unknown") for doc in roles_ref.stream()}
        
        # 2. Fetch all user profiles.
        users_ref = db.collection("user_profiles")
        profiles = []
        for doc in users_ref.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            
            # 3. Ensure the email from Firebase Auth is the source of truth.
            auth_email = _get_auth_email(doc.id)
            if auth_email:
                data["email"] = auth_email
            
            # 4. Look up the role_id from the profile and get the designation from our map.
            role_id = data.get("role_id")
            if role_id in roles_map:
                # Add the 'role' field with the string designation (e.g., "admin").
                data["role"] = roles_map[role_id]
            else:
                data["role"] = "Not Assigned" # Fallback
                
            profiles.append(data)
            
        return profiles

    profiles_with_roles = await asyncio.to_thread(_fetch_profiles_and_roles)
    return profiles_with_roles


@router.post("/", status_code=201)
async def admin_create_user_and_profile(
    request: Request,
    user_data: Dict[str, Any] = Body(...),  # 👈 CHANGED to Dict
    decoded=Depends(allowed_users(["admin"]))
):
    """
    Admin: Create a new user in Firebase Auth and their corresponding Firestore profile.
    This is different from public /auth/signup.
    """
    
    # 1. Manually validate required fields from the Dict
    email = user_data.get("email")
    password = user_data.get("password")
    role_id = user_data.get("role_id")

    if not email or not password or not role_id:
        raise HTTPException(
            status_code=422, 
            detail="Missing required fields: 'email', 'password', and 'role_id' are required."
        )

    # 2. Create the user in Firebase Authentication
    try:
        fb_user = firebase_auth.create_user(
            email=email, 
            password=password
        )
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {email} already exists.")
    except Exception as e:
        # If this fails, we don't need to roll back anything
        raise HTTPException(status_code=400, detail=f"Failed to create Firebase auth user: {e}")

    # 3. Prepare the profile document for Firestore
    now = datetime.utcnow().isoformat()
    
    # Copy the user_data dict to create the profile
    profile_data = user_data.copy()
    profile_data.pop("password")  # 👈 NEVER save the password in Firestore

    # Add/overwrite essential fields
    profile_data.update({
        "id": fb_user.uid,
        "user_id": fb_user.uid,
        "created_at": now,
        "updated_at": now,
        "deleted": False,
        "email": fb_user.email  # 👈 Always use the email from Firebase Auth as source of truth
    })

    # 4. Save the profile document in Firestore (in a thread)
    def _create_doc():
        try:
            doc_ref = db.collection("user_profiles").document(fb_user.uid)
            # Use set() here, not merge, since it's a new document
            doc_ref.set(profile_data) 
            
            saved = doc_ref.get().to_dict()
            saved["id"] = fb_user.uid
            return saved
        except Exception as e:
            # If Firestore fails, we MUST delete the auth user (rollback)
            try:
                firebase_auth.delete_user(fb_user.uid)
            except Exception as rollback_e:
                # This is bad: we have a "zombie" auth user
                raise HTTPException(status_code=500, detail=f"Failed to create profile, AND failed to rollback auth user: {rollback_e}")
            raise HTTPException(status_code=500, detail=f"Failed to create Firestore profile: {e}")

    created_profile = await asyncio.to_thread(_create_doc)
    
    # Return a consistent response (no tokens, since this is an admin action)
    return build_login_like_response(
        fb_user.uid, 
        fb_user.email, 
        "", 
        "", 
        created_profile, 
        "Admin successfully created new user and profile"
    )


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
