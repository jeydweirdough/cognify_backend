from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from database.models import Assessment, AssessmentBase
from services import assessment_service
from core.security import allowed_users

router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.post("/", response_model=Assessment, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def create_assessment(payload: AssessmentBase):
    try:
        return await assessment_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[Assessment])
async def list_assessments(decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    return await assessment_service.get_all()

@router.get("/deleted", response_model=List[Assessment], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_assessments(decoded=Depends(allowed_users(["admin"]))):
    return await assessment_service.get_all(deleted_status="deleted-only")

@router.get("/{id}", response_model=Assessment)
async def get_assessment(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    assessment = await assessment_service.get(id)
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return assessment

@router.get("/deleted/{id}", response_model=Assessment, dependencies=[Depends(allowed_users(["admin"]))])
async def get_single_deleted_assessment(id: str):
    assessment = await assessment_service.get(id, include_deleted=True)
    if not assessment or not assessment.deleted:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted assessment not found.")
    return assessment

@router.put("/{id}", response_model=Assessment, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def update_assessment(id: str, payload: AssessmentBase):
    try:
        return await assessment_service.update(id, payload)
    except HTTPException as e:
        raise e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def delete_assessment(id: str):
    try:
        await assessment_service.delete(id)
        return None
    except HTTPException as e:
        raise e

@router.post("/restore/{id}", response_model=Assessment, dependencies=[Depends(allowed_users(["admin"]))])
async def restore_assessment(id: str):
    try:
        return await assessment_service.restore(id)
    except HTTPException as e:
        raise e