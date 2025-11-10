# routes/recommendations.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
# --- FIX: Import models and services for the refactored Recommendation ---
from database.models import Recommendation, RecommendationBase, PaginatedResponse
from services import recommendation_service
from services.recommender import generate_recommendations_from_diagnostic
# --- END FIX ---
from core.security import allowed_users

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.post("/generate/{diagnostic_result_id}", response_model=List[Recommendation])
async def generate_recommendations(
    diagnostic_result_id: str,
    decoded=Depends(allowed_users(["student"]))
):
    """
    [Student] Triggers the generation of new recommendations based on
    a diagnostic test result.
    """
    try:
        recs = await generate_recommendations_from_diagnostic(diagnostic_result_id)
        if not recs:
            raise HTTPException(status_code=404, detail="No recommendations generated. Student may have passed all sections.")
        return recs
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")


@router.get("/by_student/{student_id}", response_model=PaginatedResponse[Recommendation])
async def get_student_recommendations(
    student_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 10,
    start_after: Optional[str] = None
):
    """
    [All] Get all recommendations for a specific student.
    Students can only view their own.
    """
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    if caller_role == "student" and student_id != caller_uid:
        raise HTTPException(status_code=403, detail="You can only view your own recommendations")

    items, last_id = await recommendation_service.where(
        "user_id", "==", student_id,
        limit=limit,
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/", response_model=PaginatedResponse[Recommendation], dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def list_recommendations(
    limit: int = 20,
    start_after: Optional[str] = None
):
    """[Admin/Faculty] List all recommendations in the system."""
    items, last_id = await recommendation_service.get_all(limit=limit, start_after=start_after)
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/{id}", response_model=Recommendation)
async def get_recommendation(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    """[All] Get a single recommendation by its ID."""
    rec = await recommendation_service.get(id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    
    caller_role = decoded.get("role")
    if caller_role == "student" and rec.user_id != decoded.get("uid"):
        raise HTTPException(status_code=403, detail="Access denied")

    return rec