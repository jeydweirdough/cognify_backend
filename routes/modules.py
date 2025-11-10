# routes/modules.py
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi import UploadFile, File
from typing import List, Dict, Optional
# --- NEW: Import PaginatedResponse ---
from database.models import Module, ModuleBase, PaginatedResponse
from services import module_service
from core.security import allowed_users
from firebase_admin import storage
import uuid

router = APIRouter(prefix="/modules", tags=["Modules"])

@router.post("/upload", response_model=Dict[str, str])
async def upload_module_file(
    file: UploadFile = File(...),
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    try:
        bucket = storage.bucket()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Firebase Storage bucket not configured. Make sure FIREBASE_STORAGE_BUCKET is set. Error: {e}"
        )
    try:
        ext = file.filename.split('.')[-1]
        if len(ext) > 5 or len(ext) < 2:
            ext = "bin"
    except:
        ext = "bin"
        
    unique_filename = f"modules/{uuid.uuid4()}.{ext}"
    
    try:
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(
            file.file,
            content_type=file.content_type
        )
        blob.make_public()
        return {"file_url": blob.public_url}
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")
    finally:
        await file.close()

@router.post("/", response_model=Module, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def create_module(payload: ModuleBase):
    try:
        return await module_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- NEW: Endpoint to get modules for a specific subject ---
@router.get("/by_subject/{subject_id}", response_model=PaginatedResponse[Module])
async def list_modules_for_subject(
    subject_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 50,
    start_after: Optional[str] = None
):
    """[All] Lists all non-deleted modules for a specific subject."""
    items, last_id = await module_service.where(
        "subject_id", "==", subject_id, 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)
# --- END NEW ENDPOINT ---

@router.get("/", response_model=PaginatedResponse[Module])
async def list_modules(
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await module_service.get_all(limit=limit, start_after=start_after)
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/deleted", response_model=PaginatedResponse[Module], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_modules(
    decoded=Depends(allowed_users(["admin"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await module_service.get_all(
        deleted_status="deleted-only", 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/{id}", response_model=Module)
async def get_module(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    module = await module_service.get(id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return module

@router.get("/deleted/{id}", response_model=Module, dependencies=[Depends(allowed_users(["admin"]))])
async def get_single_deleted_module(id: str):
    module = await module_service.get(id, include_deleted=True)
    if not module or not module.deleted:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted module not found.")
    return module

@router.put("/{id}", response_model=Module, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def update_module(id: str, payload: ModuleBase):
    try:
        return await module_service.update(id, payload)
    except HTTPException as e:
        raise e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def delete_module(id: str):
    try:
        await module_service.delete(id)
        return None
    except HTTPException as e:
        raise e

@router.post("/restore/{id}", response_model=Module, dependencies=[Depends(allowed_users(["admin"]))])
async def restore_module(id: str):
    try:
        return await module_service.restore(id)
    except HTTPException as e:
        raise e