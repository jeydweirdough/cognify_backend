from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from database.models import Module, ModuleBase
from services import module_service
from core.security import allowed_users

router = APIRouter(prefix="/modules", tags=["Modules"])

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