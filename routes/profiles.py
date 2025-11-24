# routes/profiles.py - REFACTORED (Removed redundant models)
from fastapi import APIRouter, HTTPException, Request, Depends, Body, status, UploadFile, File
from datetime import datetime
from firebase_admin import auth as firebase_auth
from firebase_admin import storage
from core.firebase import db
from core.security import allowed_users
import asyncio
from typing import Dict, Any, Optional, List
import uuid

# --- IMPORT ALL MODELS FROM database/models.py ---
from database.models import (
    UserProfileBase, 
    UserProfileModel, 
    PaginatedResponse
)
from services import profile_service, activity_service, recommendation_service
from services.generic_service import FirestoreModelService 
from pydantic import BaseModel
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/profiles", tags=["User Profiles"])

# Helper functions remain the same
def build_login_like_response(uid: str, email: Optional[str], token: str, refresh_token: str, profile: Dict[str, Any], message: str):
    data = {"email": email, "uid": uid, "profile": profile, "message": message}
    if token and refresh_token: 
        data.update({"token": token, "refresh_token": refresh_token})
    return data

def _get_auth_email(uid: str) -> Optional[str]:
    try: 
        return firebase_auth.get_user(uid).email
    except Exception: 
        return None

@router.get("/all")
async def get_all_profiles(
    request: Request, 
    decoded=Depends(allowed_users(["admin", "faculty_member"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    """[Admin/Faculty] Get all user profiles with pagination"""
    caller_role = decoded.get("role")
    
    def _fetch_profiles_and_roles_sync(limit: int, start_after: Optional[str]):
        roles_ref = db.collection("roles")
        roles_map = {doc.id: doc.to_dict().get("designation", "Unknown") for doc in roles_ref.stream()}
        student_role_id = next((role_id for role_id, designation in roles_map.items() if designation == "student"), None)
        
        base_query = db.collection("user_profiles").where(filter=FieldFilter("deleted", "!=", True))
        
        if caller_role == "faculty_member":
            if not student_role_id: 
                return []
            query = base_query.where(filter=FieldFilter("role_id", "==", student_role_id))
        else:
            query = base_query
        
        if start_after:
            try:
                start_doc = db.collection("user_profiles").document(start_after).get()
                if start_doc.exists:
                    query = query.start_after(start_doc)
            except Exception as e:
                print(f"Warning: Invalid start_after document ID '{start_after}': {e}")

        docs = list(query.limit(limit).stream())
            
        profiles = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            auth_email = _get_auth_email(doc.id)
            if auth_email: 
                data["email"] = auth_email
            role_id = data.get("role_id")
            data["role"] = roles_map.get(role_id, "Not Assigned")
            profiles.append(data)
            
        last_doc_id = docs[-1].id if docs else None
        
        return {"items": profiles, "last_doc_id": last_doc_id}

    profiles_data = await asyncio.to_thread(_fetch_profiles_and_roles_sync, limit, start_after)
    return profiles_data

@router.get("/", status_code=200, response_model=UserProfileModel) 
async def get_personal_profile(
    request: Request, 
    decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))
):
    """[All] Get the authenticated user's own profile"""
    uid = decoded.get("uid")
    profile = await profile_service.get(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/", status_code=201, response_model=UserProfileModel)
async def admin_create_user_and_profile(
    user_data: UserProfileBase,  # ✅ USING BASE MODEL DIRECTLY
    password: str = Body(..., embed=True),  # Password as separate field
    decoded=Depends(allowed_users(["admin"]))
):
    """[Admin] Create a new user with any role"""
    try:
        fb_user = firebase_auth.create_user(
            email=user_data.email, 
            password=password
        )
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {user_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create Firebase auth user: {e}")

    try:
        return await profile_service.create(user_data, doc_id=fb_user.uid)
    except Exception as e:
        try:
            firebase_auth.delete_user(fb_user.uid)
        except Exception as rollback_e:
            raise HTTPException(status_code=500, detail=f"CRITICAL: Profile creation failed, AND auth user rollback failed. {rollback_e}")
        raise HTTPException(status_code=400, detail=f"Failed to create Firestore profile: {e}")

@router.get("/{user_id}", response_model=UserProfileModel)
async def get_profile(
    user_id: str, 
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Admin/Faculty] Get any user's profile"""
    profile = await profile_service.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/{user_id}", response_model=UserProfileModel)
async def update_profile(
    user_id: str,
    update_data: UserProfileBase,
    decoded=Depends(allowed_users(["admin", "student", "faculty_member"]))
):
    """[All] Update a user profile (users can only update their own)"""
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    if caller_role != "admin" and user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You may only update your own profile.")

    if update_data.email:
        try:
            firebase_auth.update_user(user_id, email=update_data.email)
        except firebase_auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail="Firebase user not found.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to update Firebase email: {e}")

    try:
        updated_profile = await profile_service.update(user_id, update_data)
        
        auth_email = _get_auth_email(user_id)
        if auth_email and updated_profile.email != auth_email:
            return await profile_service.update(user_id, UserProfileBase(email=auth_email))

        return updated_profile
    except HTTPException as e:
        raise e

@router.delete("/{user_id}", response_model=UserProfileModel)
async def delete_profile(
    user_id: str, 
    decoded=Depends(allowed_users(["admin"]))
):
    """[Admin] Soft-delete a user profile"""
    try:
        await profile_service.delete(user_id)
        
        updated_profile = await profile_service.get(user_id, include_deleted=True)
        if not updated_profile:
            raise HTTPException(status_code=404, detail="Profile not found after delete.")
        return updated_profile
    except HTTPException as e:
        raise e

@router.post("/upload_profile_picture", response_model=Dict[str, str])
async def upload_profile_picture(
    file: UploadFile = File(...),
    decoded=Depends(allowed_users(["admin", "student", "faculty_member"]))
):
    """[All Users] Upload a profile picture and auto-update profile"""
    caller_uid = decoded.get("uid")
    
    try:
        bucket = storage.bucket()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Firebase Storage bucket not configured. Error: {e}"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        ext = file.filename.split('.')[-1]
        if len(ext) > 5 or len(ext) < 2:
            ext = "jpg"
    except:
        ext = "jpg"
    
    unique_filename = f"profile_pictures/{caller_uid}_{uuid.uuid4()}.{ext}"
    
    try:
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(file.file, content_type=file.content_type)
        blob.make_public()
        
        # Auto-update profile with new image URL
        update_data = UserProfileBase(
            email="",  # Required field but won't be updated
            profile_picture=blob.public_url,
            image=blob.public_url
        )
        await profile_service.update(caller_uid, update_data)
        
        return {
            "file_url": blob.public_url,
            "message": "Profile picture uploaded and updated successfully"
        }
    except Exception as e:
        print(f"Error uploading profile picture: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload: {e}")
    finally:
        await file.close()

# Device token registration - kept as simple Pydantic model (not a profile field)
class DeviceTokenPayload(BaseModel):
    fcm_token: str

@router.post("/register_device", status_code=status.HTTP_200_OK)
async def register_device_token(
    payload: DeviceTokenPayload,
    decoded=Depends(allowed_users(["student"]))
):
    """[Student] Register device for push notifications"""
    caller_uid = decoded.get("uid")
    try:
        update_data = UserProfileBase(
            email="",  # Required but won't update
            fcm_token=payload.fcm_token
        )
        await profile_service.update(caller_uid, update_data)
        return {"message": "Device registered successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error registering device for {caller_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register device: {e}")

@router.post("/{user_id}/purge", response_model=Dict[str, Any])
async def purge_user_and_data(
    user_id: str,
    decoded=Depends(allowed_users(["admin"]))
):
    """[Admin] PERMANENTLY delete user and all associated data"""
    
    # 1. Delete from Firebase Authentication
    try:
        await asyncio.to_thread(firebase_auth.delete_user, user_id)
        print(f"Successfully deleted auth user: {user_id}")
    except firebase_auth.UserNotFoundError:
        print(f"Auth user {user_id} not found (already deleted?).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete auth user: {e}")

    # 2. Delete the main Firestore Profile
    await profile_service.delete_permanent(user_id)
    
    # 3. Cascade delete related data
    deleted_activities = await activity_service.purge_where(
        field="user_id", operator="==", value=user_id
    )
    
    deleted_recs = await recommendation_service.purge_where(
        field="user_id", operator="==", value=user_id
    )
    
    # 4. Delete student motivation document
    motivation_service_temp = FirestoreModelService(
        collection_name="student_motivations",
        model=BaseModel 
    )
    motivation_doc_deleted = await motivation_service_temp.delete_permanent(user_id)
    deleted_motivations = 1 if motivation_doc_deleted else 0

    return {
        "message": f"User {user_id} and all related data have been purged.",
        "auth_user_deleted": True,
        "profile_document_deleted": True,
        "related_data_purged": {
            "activities": deleted_activities,
            "recommendations": deleted_recs,
            "student_motivations": deleted_motivations
        }
    }