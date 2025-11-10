from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from database.models import ContentVerification, ContentVerificationBase, PaginatedResponse
from services import content_verification_service
from core.security import allowed_users

router = APIRouter(prefix="/content_verification", tags=["Content Verification"])

@router.post("/", response_model=ContentVerification, status_code=status.HTTP_201_CREATED)
async def submit_content_for_verification(
    payload: ContentVerificationBase,
    decoded=Depends(allowed_users(["faculty_member", "admin"]))
):
    """
    [Faculty/Admin] Submit content (module/quiz/assessment) for verification.
    Faculty members verify content created by others or by AI.
    """
    payload.verified_by = decoded["uid"]
    
    try:
        return await content_verification_service.create(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pending", response_model=PaginatedResponse[ContentVerification])
async def get_pending_verifications(
    decoded=Depends(allowed_users(["admin", "faculty_member"])),
    limit: int = 50,
    start_after: Optional[str] = None
):
    """[Faculty/Admin] Get all content awaiting verification"""
    items, last_id = await content_verification_service.where(
        "verification_status", "==", "pending",
        limit=limit,
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/by_content/{content_id}", response_model=List[ContentVerification])
async def get_verifications_for_content(
    content_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Faculty/Admin] Get all verification records for a specific content item"""
    items, _ = await content_verification_service.where(
        "content_id", "==", content_id,
        limit=100
    )
    return items


@router.get("/by_status/{status_value}", response_model=PaginatedResponse[ContentVerification])
async def get_verifications_by_status(
    status_value: str,
    decoded=Depends(allowed_users(["admin", "faculty_member"])),
    limit: int = 50,
    start_after: Optional[str] = None
):
    """[Faculty/Admin] Get verifications by status (approved/rejected/needs_revision)"""
    if status_value not in ["approved", "rejected", "needs_revision", "pending"]:
        raise HTTPException(status_code=400, detail="Invalid status value")
    
    items, last_id = await content_verification_service.where(
        "verification_status", "==", status_value,
        limit=limit,
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)


@router.get("/{verification_id}", response_model=ContentVerification)
async def get_verification(
    verification_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Faculty/Admin] Get a single verification record"""
    verification = await content_verification_service.get(verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification record not found")
    return verification


@router.put("/{verification_id}", response_model=ContentVerification)
async def update_verification_status(
    verification_id: str,
    payload: ContentVerificationBase,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Faculty/Admin] Update a verification record (approve/reject/request revision)"""
    try:
        return await content_verification_service.update(verification_id, payload)
    except HTTPException as e:
        raise e


@router.delete("/{verification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_verification(
    verification_id: str,
    decoded=Depends(allowed_users(["admin"]))
):
    """[Admin] Delete a verification record"""
    try:
        await content_verification_service.delete(verification_id)
        return None
    except HTTPException as e:
        raise e