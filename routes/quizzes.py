# routes/quizzes.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from database.models import Quiz, QuizBase, PaginatedResponse
from services import quiz_service
from core.security import allowed_users

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

@router.post("/", response_model=Quiz, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def create_quiz(payload: QuizBase):
    try:
        return await quiz_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=PaginatedResponse[Quiz])
async def list_quizzes(
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await quiz_service.get_all(limit=limit, start_after=start_after)
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/deleted", response_model=PaginatedResponse[Quiz], dependencies=[Depends(allowed_users(["admin"]))])
async def list_deleted_quizzes(
    decoded=Depends(allowed_users(["admin"])),
    limit: int = 20,
    start_after: Optional[str] = None
):
    items, last_id = await quiz_service.get_all(
        deleted_status="deleted-only", 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/{id}", response_model=Quiz)
async def get_quiz(id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    quiz = await quiz_service.get(id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return quiz

@router.get("/deleted/{id}", response_model=Quiz, dependencies=[Depends(allowed_users(["admin"]))])
async def get_single_deleted_quiz(id: str):
    quiz = await quiz_service.get(id, include_deleted=True)
    if not quiz or not quiz.deleted:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted quiz not found.")
    return quiz

@router.put("/{id}", response_model=Quiz, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def update_quiz(id: str, payload: QuizBase):
    try:
        return await quiz_service.update(id, payload)
    except HTTPException as e:
        raise e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def delete_quiz(id: str):
    try:
        await quiz_service.delete(id)
        return None
    except HTTPException as e:
        raise e

@router.post("/restore/{id}", response_model=Quiz, dependencies=[Depends(allowed_users(["admin"]))])
async def restore_quiz(id: str):
    try:
        return await quiz_service.restore(id)
    except HTTPException as e:
        raise e