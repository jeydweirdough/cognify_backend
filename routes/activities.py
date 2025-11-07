# routes/activities.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from database.models import Activity, ActivityBase, PaginatedResponse
from services import activity_service
from core.security import allowed_users

router = APIRouter(prefix="/activities", tags=["Activities"])

@router.post("/", response_model=Activity, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def create_activity(payload: ActivityBase):
    try: return await activity_service.create(payload)
    except Exception as e: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=PaginatedResponse[Activity])
async def list_activities(
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await activity_service.get_all(limit=limit, start_after=start_after)
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/deleted", response_model=PaginatedResponse[Activity], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_activities(
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await activity_service.get_all(
        deleted_status="deleted-only", 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/{id}", response_model=Activity)
async def get_activity(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    activity = await activity_service.get(id)
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return activity

@router.get("/deleted/{id}", response_model=Activity, dependencies=[Depends(allowed_users(["admin"]))])
async def get_single_deleted_activity(id: str):
    activity = await activity_service.get(id, include_deleted=True)
    if not activity or not activity.deleted:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted activity not found.")
    return activity

@router.put("/{id}", response_model=Activity, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def update_activity(id: str, payload: ActivityBase):
    try: return await activity_service.update(id, payload)
    except HTTPException as e: raise e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def delete_activity(id: str):
    try:
        await activity_service.delete(id)
        return None
    except HTTPException as e: raise e

@router.post("/restore/{id}", response_model=Activity, dependencies=[Depends(allowed_users(["admin"]))])
async def restore_activity(id: str):
    try: return await activity_service.restore(id)
    except HTTPException as e: raise e