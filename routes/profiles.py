# routes/profiles.py
from fastapi import APIRouter, HTTPException, Request, Depends, Body, status
from datetime import datetime
from firebase_admin import auth as firebase_auth
from core.firebase import db
from core.security import allowed_users
import asyncio
from typing import Dict, Any, Optional, List
from database.models import UserProfileBase, UserProfileModel, PaginatedResponse
from pydantic import BaseModel, EmailStr, Field 
from routes import auth
from services import profile_service
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/profiles", tags=["User Profiles"])

class AdminCreateUserSchema(UserProfileBase):
    password: str

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_id: Optional[str] = None
    pre_assessment_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    current_module: Optional[str] = None
    fcm_token: Optional[str] = None

def build_login_like_response(uid: str, email: Optional[str], token: str, refresh_token: str, profile: Dict[str, Any], message: str):
    data = {"email": email, "uid": uid, "profile": profile, "message": message}
    if token and refresh_token: data.update({"token": token, "refresh_token": refresh_token})
    return data
def _get_auth_email(uid: str) -> Optional[str]:
    try: return firebase_auth.get_user(uid).email
    except Exception: return None

@router.get("/all")
async def get_all_profiles(
    request: Request, 
    decoded=Depends(allowed_users(["admin", "faculty_member"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    caller_role = decoded.get("role")
    
    def _fetch_profiles_and_roles_sync(limit: int, start_after: Optional[str]):
        roles_ref = db.collection("roles")
        roles_map = {doc.id: doc.to_dict().get("designation", "Unknown") for doc in roles_ref.stream()}
        student_role_id = next((role_id for role_id, designation in roles_map.items() if designation == "student"), None)
        
        base_query = db.collection("user_profiles").where(filter=FieldFilter("deleted", "!=", True))
        
        if caller_role == "faculty_member":
            if not student_role_id: return []
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
            data = doc.to_dict(); data["id"] = doc.id
            auth_email = _get_auth_email(doc.id)
            if auth_email: data["email"] = auth_email
            role_id = data.get("role_id")
            data["role"] = roles_map.get(role_id, "Not Assigned")
            profiles.append(data)
            
        last_doc_id = docs[-1].id if docs else None
        
        return {"items": profiles, "last_doc_id": last_doc_id}

    profiles_data = await asyncio.to_thread(_fetch_profiles_and_roles_sync, limit, start_after)
    return profiles_data

@router.get("/", status_code=200, response_model=UserProfileModel) 
async def get_personal_profile(request: Request, decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))):
    uid = decoded.get("uid")
    profile = await profile_service.get(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/", status_code=201, response_model=UserProfileModel)
async def admin_create_user_and_profile(
    user_data: AdminCreateUserSchema,
    decoded=Depends(allowed_users(["admin"]))
):
    try:
        fb_user = firebase_auth.create_user(
            email=user_data.email, 
            password=user_data.password
        )
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"Account with email {user_data.email} already exists.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create Firebase auth user: {e}")

    try:
        profile_data = user_data.model_dump(exclude={"password"})
        profile_data["email"] = fb_user.email
        profile_payload = UserProfileBase(**profile_data)
        return await profile_service.create(profile_payload, doc_id=fb_user.uid)
    except Exception as e:
        try:
            firebase_auth.delete_user(fb_user.uid)
        except Exception as rollback_e:
            raise HTTPException(status_code=500, detail=f"CRITICAL: Profile creation failed, AND auth user rollback failed. {rollback_e}")
        raise HTTPException(status_code=400, detail=f"Failed to create Firestore profile: {e}")

@router.get("/{user_id}", response_model=UserProfileModel)
async def get_profile(user_id: str, decoded=Depends(allowed_users(["admin", "faculty_member"]))):
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
            return await profile_service.update(user_id, UserProfileUpdate(email=auth_email))

        return updated_profile
    except HTTPException as e:
        raise e

@router.delete("/{user_id}", response_model=UserProfileModel, dependencies=[Depends(allowed_users(["admin"]))])
async def delete_profile(user_id: str, decoded=Depends(allowed_users(["admin"]))):
    try:
        await profile_service.delete(user_id)
        
        updated_profile = await profile_service.get(user_id, include_deleted=True)
        if not updated_profile:
             raise HTTPException(status_code=404, detail="Profile not found after delete.")
        return updated_profile
    except HTTPException as e:
        raise e

class DeviceTokenPayload(BaseModel):
    fcm_token: str = Field(..., description="Firebase Cloud Messaging device token")

@router.post("/register_device", status_code=status.HTTP_200_OK)
async def register_device_token(
    payload: DeviceTokenPayload,
    decoded=Depends(allowed_users(["student"]))
):
    caller_uid = decoded.get("uid")
    try:
        update_data = UserProfileUpdate(fcm_token=payload.fcm_token)
        await profile_service.update(caller_uid, update_data)
        return {"message": "Device registered successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error registering device for {caller_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register device: {e}")