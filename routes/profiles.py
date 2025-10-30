# routes/profiles.py

from fastapi import APIRouter, HTTPException, Request, Depends, Body, status
from datetime import datetime
from firebase_admin import auth as firebase_auth
from core.firebase import db
from core.security import allowed_users
import asyncio
from typing import Dict, Any, Optional, List
from database.models import UserProfileBase, UserProfileModel
from pydantic import BaseModel, EmailStr
from routes import auth
from services import profile_service
from google.cloud.firestore_v1.base_query import FieldFilter # Import FieldFilter

router = APIRouter(prefix="/profiles", tags=["User Profiles"])

# --- FIX: AdminCreateUserSchema no longer needs student_id ---
class AdminCreateUserSchema(UserProfileBase):
    """
    Special schema for admin user creation.
    Inherits all fields from UserProfileBase (email, role_id, etc.)
    and adds a password.
    """
    password: str
    # email is inherited from UserProfileBase

class UserProfileUpdate(BaseModel):
    """Schema for partial profile updates."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_id: Optional[str] = None
    pre_assessment_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    current_module: Optional[str] = None

# ... (build_login_like_response and _get_auth_email are fine) ...
def build_login_like_response(uid: str, email: Optional[str], token: str, refresh_token: str, profile: Dict[str, Any], message: str):
    data = {"email": email, "uid": uid, "profile": profile, "message": message}
    if token and refresh_token: data.update({"token": token, "refresh_token": refresh_token})
    return data
def _get_auth_email(uid: str) -> Optional[str]:
    try: return firebase_auth.get_user(uid).email
    except Exception: return None


@router.get("/all")
async def get_all_profiles(request: Request, decoded=Depends(allowed_users(["admin", "faculty_member"]))):
    """[Admin/Faculty] Get all user profiles."""
    caller_role = decoded.get("role")
    def _fetch_profiles_and_roles():
        roles_ref = db.collection("roles")
        roles_map = {doc.id: doc.to_dict().get("designation", "Unknown") for doc in roles_ref.stream()}
        student_role_id = next((role_id for role_id, designation in roles_map.items() if designation == "student"), None)
        
        # --- FIX: Use filter= to remove UserWarning ---
        base_query = db.collection("user_profiles").where(filter=FieldFilter("deleted", "!=", True))
        
        if caller_role == "faculty_member":
            if not student_role_id: return []
            query = base_query.where(filter=FieldFilter("role_id", "==", student_role_id))
        else:
            query = base_query
            
        profiles = []
        for doc in query.stream():
            data = doc.to_dict(); data["id"] = doc.id
            auth_email = _get_auth_email(doc.id)
            if auth_email: data["email"] = auth_email
            role_id = data.get("role_id")
            data["role"] = roles_map.get(role_id, "Not Assigned")
            profiles.append(data)
        return profiles
    profiles_with_roles = await asyncio.to_thread(_fetch_profiles_and_roles)
    return profiles_with_roles


@router.get("/", status_code=200, response_model=UserProfileModel) 
async def get_personal_profile(request: Request, decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))):
    """Get the profile of the currently authenticated user."""
    uid = decoded.get("uid")
    profile = await profile_service.get(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/", status_code=201, response_model=UserProfileModel)
async def admin_create_user_and_profile(
    user_data: AdminCreateUserSchema, # No request needed
    decoded=Depends(allowed_users(["admin"]))
):
    """
    [Admin Only] Create a new user in Firebase Auth and their Firestore profile.
    - Uses AdminCreateUserSchema (full profile + password).
    - Uses the 'role_id' from the request body.
    """
    # 1. Create Auth user
    try:
        fb_user = firebase_auth.create_user(
            email=user_data.email, 
            password=user_data.password
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {user_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create Firebase auth user: {e}")

    # 2. Create Profile
    try:
        # --- FIX: This is the logic that fixes the screenshot error ---
        # 1. Dump all data from the request (which includes email, role_id, etc.)
        profile_data = user_data.model_dump(exclude={"password"})
        
        # 2. Override the email with the one from the created auth user
        #    This ensures they are in sync.
        profile_data["email"] = fb_user.email
        
        # 3. Create the UserProfileBase object from this clean dict
        profile_payload = UserProfileBase(**profile_data)
        
        # 4. Use our service to create the doc, using the Auth UID as the doc ID
        return await profile_service.create(profile_payload, doc_id=fb_user.uid)
        
    except Exception as e:
        # --- ROLLBACK ---
        try:
            firebase_auth.delete_user(fb_user.uid)
        except Exception as rollback_e:
            raise HTTPException(status_code=500, detail=f"CRITICAL: Profile creation failed, AND auth user rollback failed. {rollback_e}")
        raise HTTPException(status_code=400, detail=f"Failed to create Firestore profile: {e}")


@router.get("/{user_id}", response_model=UserProfileModel)
async def get_profile(user_id: str, decoded=Depends(allowed_users(["admin", "faculty_member"]))):
    """[Admin/Faculty] view a specific profile by ID."""
    profile = await profile_service.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{user_id}", response_model=UserProfileModel)
async def update_profile(
    user_id: str,
    update_data: UserProfileUpdate,
    decoded=Depends(allowed_users(["admin", "student", "faculty_member"]))
):
    """[Admin/User] update a profile. Syncs with Firebase Auth email."""
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    if caller_role != "admin" and user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You may only update your own profile.")

    # 1. Custom logic: Sync email with Firebase Auth
    if update_data.email:
        try:
            firebase_auth.update_user(user_id, email=update_data.email)
        except firebase_auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail="Firebase user not found.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to update Firebase email: {e}")

    # 2. Use our service to update Firestore
    try:
        updated_profile = await profile_service.update(user_id, update_data)
        
        # 3. Post-update sync
        auth_email = _get_auth_email(user_id)
        if auth_email and updated_profile.email != auth_email:
            # Sync email in DB to match auth email
            return await profile_service.update(user_id, UserProfileUpdate(email=auth_email))

        return updated_profile
    except HTTPException as e:
        raise e

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin"]))])
async def delete_profile(user_id: str, decoded=Depends(allowed_users(["admin"]))):
    """[Admin Only] Soft-delete a profile."""
    try:
        await profile_service.delete(user_id)
        return None
    except HTTPException as e:
        raise e