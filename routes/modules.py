from fastapi import APIRouter, HTTPException, status, Depends
# --- NEW: Added UploadFile, File ---
from fastapi import UploadFile, File
from typing import List, Dict
from database.models import Module, ModuleBase
from services import module_service
from core.security import allowed_users
# --- NEW: Added storage and uuid ---
from firebase_admin import storage
import uuid

router = APIRouter(prefix="/modules", tags=["Modules"])

# --- NEW ENDPOINT FOR FILE UPLOADS ---
@router.post("/upload", response_model=Dict[str, str])
async def upload_module_file(
    file: UploadFile = File(...),
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Uploads a module file (like a PDF) to
    Firebase Storage and returns the public URL.
    """
    
    # 1. Get the storage bucket
    #    This requires your core/firebase.py to be initialized with 'storageBucket'
    try:
        bucket = storage.bucket()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Firebase Storage bucket not configured. Make sure FIREBASE_STORAGE_BUCKET is set. Error: {e}"
        )

    # 2. Create a unique, secure filename
    #    We use a UUID to prevent filename collisions and guessing
    try:
        # Try to get the file extension, default to .bin if not found
        ext = file.filename.split('.')[-1]
        if len(ext) > 5 or len(ext) < 2:
            ext = "bin" # Default for unknown
    except:
        ext = "bin"
        
    unique_filename = f"modules/{uuid.uuid4()}.{ext}"
    
    # 3. Upload the file
    try:
        blob = bucket.blob(unique_filename)
        
        # Use file.file which is the SpooledTemporaryFile
        blob.upload_from_file(
            file.file,
            content_type=file.content_type
        )
        
        # 4. Make the file public (so students can read it)
        blob.make_public()
        
        # 5. Return the public URL
        return {"file_url": blob.public_url}
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")
    finally:
        # 6. Always close the file
        await file.close()

@router.post("/", response_model=Module, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def create_module(payload: ModuleBase):
    try:
        return await module_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[Module])
async def list_modules(decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    return await module_service.get_all()

@router.get("/deleted", response_model=List[Module], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_modules(decoded=Depends(allowed_users(["admin"]))):
    return await module_service.get_all(deleted_status="deleted-only")

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