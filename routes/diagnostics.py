# routes/diagnostics.py
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List, Optional
from database.models import (
    DiagnosticAssessment, DiagnosticAssessmentBase,
    DiagnosticResult, DiagnosticResultBase,
    TOSPerformance, PaginatedResponse
)
from services import diagnostic_service, diagnostic_result_service
from core.security import allowed_users

# --- NEW: Import the enhanced recommender service ---
from services.recommender import generate_recommendations_from_diagnostic

router = APIRouter(prefix="/diagnostics", tags=["Diagnostic Assessments"])

# ============================================================
# DIAGNOSTIC ASSESSMENT ENDPOINTS (Faculty/Admin)
# ============================================================
@router.post("/assessments", response_model=DiagnosticAssessment, status_code=status.HTTP_201_CREATED)
async def create_diagnostic_assessment(
    payload: DiagnosticAssessmentBase,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Faculty/Admin] Create a new diagnostic assessment"""
    try:
        return await diagnostic_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessments", response_model=PaginatedResponse[DiagnosticAssessment])
async def list_diagnostic_assessments(
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    subject_id: Optional[str] = None,
    limit: int = 20,
    start_after: Optional[str] = None
):
    """[All] List all diagnostic assessments, optionally filtered by subject"""
    if subject_id:
        items, last_id = await diagnostic_service.where(
            "subject_id", "==", subject_id,
            limit=limit,
            start_after=start_after
        )
    else:
        items, last_id = await diagnostic_service.get_all(
            limit=limit,
            start_after=start_after
        )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/assessments/{id}", response_model=DiagnosticAssessment)
async def get_diagnostic_assessment(
    id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """[All] Get a single diagnostic assessment by ID"""
    assessment = await diagnostic_service.get(id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Diagnostic assessment not found")
    return assessment


# ============================================================
# DIAGNOSTIC RESULT ENDPOINTS (Students take the test)
# ============================================================

@router.post("/results", response_model=DiagnosticResult, status_code=status.HTTP_201_CREATED)
async def submit_diagnostic_result(
    payload: DiagnosticResultBase,
    # --- NEW: Add BackgroundTasks ---
    background_tasks: BackgroundTasks,
    decoded=Depends(allowed_users(["student"]))
):
    """
    [Student] Submit diagnostic test results.
    This will trigger the recommendation engine.
    """
    caller_uid = decoded.get("uid")
    
    # Students can only submit their own results
    if payload.user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You can only submit your own test results")
    
    try:
        result = await diagnostic_result_service.create(payload)
        
        # --- FIX: Trigger recommendation generation in background ---
        print(f"Queueing recommendation task for result: {result.id}")
        background_tasks.add_task(generate_recommendations_from_diagnostic, result.id)
        # --- END FIX ---
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/results/by_student/{student_id}", response_model=PaginatedResponse[DiagnosticResult])
async def get_student_diagnostic_results(
    student_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    """[Student/Faculty/Admin] Get all diagnostic results for a student"""
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")
    
    # Students can only view their own results
    if caller_role == "student" and student_id != caller_uid:
        raise HTTPException(status_code=403, detail="You can only view your own results")
    
    items, last_id = await diagnostic_result_service.where(
        "user_id", "==", student_id,
        limit=limit,
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/results/{id}", response_model=DiagnosticResult)
async def get_diagnostic_result(
    id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """[All] Get a single diagnostic result by ID"""
    result = await diagnostic_result_service.get(id)
    if not result:
        raise HTTPException(status_code=404, detail="Diagnostic result not found")
    
    # Students can only view their own results
    caller_role = decoded.get("role")
    if caller_role == "student" and result.user_id != decoded.get("uid"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return result


# ============================================================
# ANALYTICS: Diagnostic Performance Summary
# ============================================================

@router.get("/analytics/subject/{subject_id}")
async def get_subject_diagnostic_analytics(
    subject_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Faculty/Admin] Get aggregated diagnostic performance for a subject.
    Shows which TOS topics students are struggling with most.
    """
    from services.diagnostic_analytics import get_subject_diagnostic_summary
    
    try:
        summary = await get_subject_diagnostic_summary(subject_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))