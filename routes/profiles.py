# routes/profiles.py
from fastapi import APIRouter, HTTPException, Request, Depends, Body, status
from datetime import datetime
from firebase_admin import auth as firebase_auth
from core.firebase import db
from core.security import allowed_users
import asyncio
from typing import Dict, Any, Optional, List

# --- UPDATED IMPORTS ---
from database.models import UserProfileBase, UserProfileModel, PaginatedResponse, BaseModel
from pydantic import BaseModel, EmailStr, Field 
from routes import auth
# --- We now import the specific services we need ---
from services import profile_service, activity_service, recommendation_service
# --- We also import the base class to create a temporary service ---
from services.generic_service import FirestoreModelService 
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

# --- REMOVED THE _batch_delete_where HELPER FUNCTION ---
# It is now part of the generic service

def build_login_like_response(uid: str, email: Optional[str], token: str, refresh_token: str, profile: Dict[str, Any], message: str):
    # ... (this function is unchanged)
    data = {"email": email, "uid": uid, "profile": profile, "message": message}
    if token and refresh_token: data.update({"token": token, "refresh_token": refresh_token})
    return data
def _get_auth_email(uid: str) -> Optional[str]:
    # ... (this function is unchanged)
    try: return firebase_auth.get_user(uid).email
    except Exception: return None

@router.get("/all")
async def get_all_profiles(
    # ... (this function is unchanged)
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
async def get_personal_profile(
    # ... (this function is unchanged)
    request: Request, 
    decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))
):
    uid = decoded.get("uid")
    profile = await profile_service.get(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/", status_code=201, response_model=UserProfileModel)
async def admin_create_user_and_profile(
    # ... (this function is unchanged)
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
async def get_profile(
    # ... (this function is unchanged)
    user_id: str, 
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    profile = await profile_service.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/{user_id}", response_model=UserProfileModel)
async def update_profile(
    # ... (this function is unchanged)
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
async def delete_profile(
    # ... (this is the soft delete, unchanged)
    user_id: str, 
    decoded=Depends(allowed_users(["admin"]))
):
    try:
        await profile_service.delete(user_id)
        
        updated_profile = await profile_service.get(user_id, include_deleted=True)
        if not updated_profile:
             raise HTTPException(status_code=404, detail="Profile not found after delete.")
        return updated_profile
    except HTTPException as e:
        raise e

class DeviceTokenPayload(BaseModel):
    # ... (this class is unchanged)
    fcm_token: str = Field(..., description="Firebase Cloud Messaging device token")

@router.post("/register_device", status_code=status.HTTP_200_OK)
async def register_device_token(
    # ... (this function is unchanged)
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


# ---
# --- THIS IS THE UPDATED ENDPOINT ---
# ---
@router.post("/{user_id}/purge", response_model=Dict[str, Any])
async def purge_user_and_data(
    user_id: str,
    decoded=Depends(allowed_users(["admin"]))
):
    """
    [Admin] PERMANENTLY deletes a user and all their associated data
    from the system. This is irreversible and fixes the "clogged" data.
    
    This deletes:
    1. The Firebase Auth account.
    2. The Firestore user_profiles document.
    3. All related 'activities'.
    4. All related 'recommendations'.
    5. All related 'student_analytics_reports'.
    """
    
    # 1. Delete from Firebase Authentication (The login account)
    try:
        await asyncio.to_thread(firebase_auth.delete_user, user_id)
        print(f"Successfully deleted auth user: {user_id}")
    except firebase_auth.UserNotFoundError:
        print(f"Auth user {user_id} not found (already deleted?).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete auth user: {e}")

    # 2. Delete the main Firestore Profile document
    # We use the new 'delete_permanent' function
    await profile_service.delete_permanent(user_id)
    
    # 3. Run the cascading deletes using the new GENERIC 'purge_where'
    deleted_activities = await activity_service.purge_where(
        field="user_id", operator="==", value=user_id
    )
    
    deleted_recs = await recommendation_service.purge_where(
        field="user_id", operator="==", value=user_id
    )
    
    # 4. For collections without a service, we can create one on-the-fly
    # (The model doesn't matter since we're just deleting)
    analytics_service_temp = FirestoreModelService(
        collection_name="student_analytics_reports",
        model=BaseModel 
    )
    deleted_reports = await analytics_service_temp.purge_where(
        field="student_id", operator="==", value=user_id
    )
    
    return {
        "message": f"User {user_id} and all related data have been purged.",
        "auth_user_deleted": True,
        "profile_document_deleted": True,
        "related_data_purged": {
            "activities": deleted_activities,
            "recommendations": deleted_recs,
            "analytics_reports": deleted_reports
        }
    }