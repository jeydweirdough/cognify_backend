# routes/tos.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from database.models import TOS, TOSBase, PaginatedResponse
from services import tos_service
from core.security import allowed_users

router = APIRouter(prefix="/tos", tags=["Table Of Specifications"])

@router.post("/", response_model=TOS, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def create_tos(payload: TOSBase):
    try:
        return await tos_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/by_subject/{subject_id}", response_model=PaginatedResponse[TOS])
async def list_tos_for_subject(
    subject_id: str, 
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await tos_service.where(
        "subject_id", "==", subject_id, 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/deleted", response_model=PaginatedResponse[TOS], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_tos(
    decoded=Depends(allowed_users(["admin"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await tos_service.get_all(
        deleted_status="deleted-only", 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/{id}", response_model=TOS)
async def get_tos(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    tos = await tos_service.get(id)
    if not tos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return tos

@router.get("/deleted/{id}", response_model=TOS, dependencies=[Depends(allowed_users(["admin"]))])
async def get_single_deleted_tos(id: str):
    tos = await tos_service.get(id, include_deleted=True)
    if not tos or not tos.deleted:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted TOS not found.")
    return tos

@router.put("/{id}", response_model=TOS, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def update_tos(id: str, payload: TOSBase):
    try:
        return await tos_service.update(id, payload)
    except HTTPException as e:
        raise e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def delete_tos(id: str):
    try:
        await tos_service.delete(id)
        return None
    except HTTPException as e:
        raise e

@router.post("/restore/{id}", response_model=TOS, dependencies=[Depends(allowed_users(["admin"]))])
async def restore_tos(id: str):
    try:
        return await tos_service.restore(id)
    except HTTPException as e:
        raise e