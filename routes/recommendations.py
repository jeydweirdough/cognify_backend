# routes/recommendations.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from database.models import Recommendation, RecommendationBase, PaginatedResponse
from services import recommendation_service
from services.recommender import pick_recommendations_for_student
from core.security import allowed_users

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.post("/generate/{student_id}", dependencies=[Depends(allowed_users(["student"]))])
async def generate_recommendations(student_id: str):
    recs = await pick_recommendations_for_student(student_id)
    if not recs:
        raise HTTPException(status_code=404, detail="No recommendations generated or student not found")
    return {"generated": len(recs), "recommendations": recs}

@router.post("/", response_model=Recommendation, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin"]))])
async def create_recommendation(payload: RecommendationBase):
    try:
        return await recommendation_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=PaginatedResponse[Recommendation], dependencies=[Depends(allowed_users(["admin", "faculty_member", "student"]))])
async def list_recommendations(
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await recommendation_service.get_all(limit=limit, start_after=start_after)
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/deleted", response_model=PaginatedResponse[Recommendation], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_recommendations(
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await recommendation_service.get_all(
        deleted_status="deleted-only", 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/{id}", response_model=Recommendation)
async def get_recommendation(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    rec = await recommendation_service.get(id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return rec

@router.put("/{id}", response_model=Recommendation, dependencies=[Depends(allowed_users(["admin"]))])
async def update_recommendation(id: str, payload: RecommendationBase):
    try:
        return await recommendation_service.update(id, payload)
    except HTTPException as e:
        raise e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin"]))])
async def delete_recommendation(id: str):
    try:
        await recommendation_service.delete(id)
        return None
    except HTTPException as e:
        raise e

@router.post("/restore/{id}", response_model=Recommendation, dependencies=[Depends(allowed_users(["admin"]))])
async def restore_recommendation(id: str):
    try:
        return await recommendation_service.restore(id)
    except HTTPException as e:
        raise e