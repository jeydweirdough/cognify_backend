from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from database.models import StudySession, StudySessionBase, PaginatedResponse
from services import study_session_service
from core.security import allowed_users

router = APIRouter(prefix="/study_sessions", tags=["Study Sessions"])

@router.post("/", response_model=StudySession, status_code=status.HTTP_201_CREATED)
async def create_study_session(
    payload: StudySessionBase,
    decoded=Depends(allowed_users(["student"]))
):
    """
    [Student] Create a new study session log.
    This groups multiple activities into a single learning session.
    """
    caller_uid = decoded.get("uid")
    
    if payload.user_id != caller_uid:
        raise HTTPException(
            status_code=403, 
            detail="You can only create your own study sessions"
        )
    
    try:
        return await study_session_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by_student/{student_id}", response_model=PaginatedResponse[StudySession])
async def get_student_study_sessions(
    student_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    """
    [All] Get all study sessions for a specific student.
    Students can only view their own sessions.
    """
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")
    
    if caller_role == "student" and student_id != caller_uid:
        raise HTTPException(
            status_code=403, 
            detail="You can only view your own study sessions"
        )
    
    items, last_id = await study_session_service.where(
        "user_id", "==", student_id,
        limit=limit,
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/", response_model=PaginatedResponse[StudySession])
async def list_all_study_sessions(
    decoded=Depends(allowed_users(["admin", "faculty_member"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    """[Admin/Faculty] List all study sessions"""
    items, last_id = await study_session_service.get_all(
        limit=limit,
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/{session_id}", response_model=StudySession)
async def get_study_session(
    session_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """[All] Get a single study session by ID"""
    session = await study_session_service.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found")
    
    caller_role = decoded.get("role")
    if caller_role == "student" and session.user_id != decoded.get("uid"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return session


@router.put("/{session_id}", response_model=StudySession)
async def update_study_session(
    session_id: str,
    payload: StudySessionBase,
    decoded=Depends(allowed_users(["student"]))
):
    """[Student] Update a study session (e.g., mark as completed)"""
    caller_uid = decoded.get("uid")
    
    existing_session = await study_session_service.get(session_id)
    if not existing_session:
        raise HTTPException(status_code=404, detail="Study session not found")
    
    if existing_session.user_id != caller_uid:
        raise HTTPException(
            status_code=403, 
            detail="You can only update your own study sessions"
        )
    
    try:
        return await study_session_service.update(session_id, payload)
    except HTTPException as e:
        raise e


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study_session(
    session_id: str,
    decoded=Depends(allowed_users(["admin"]))
):
    """[Admin] Soft-delete a study session"""
    try:
        await study_session_service.delete(session_id)
        return None
    except HTTPException as e:
        raise e