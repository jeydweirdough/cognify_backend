# jeydweirdough/cognify_backend/cognify_backend-2c9bd547ece812c69eb03e791dc56811f9fbe7c8/routes/subjects.py

from fastapi import APIRouter, HTTPException, Depends
from core.firebase import db
from database.models import Subject, SubjectBase, PaginatedResponse # --- 1. Import PaginatedResponse ---
import asyncio
from datetime import datetime
from typing import List, Optional # --- 2. Import Optional ---
from core.security import allowed_users # --- 3. Import security ---
from google.cloud.firestore_v1.base_query import FieldFilter # --- 4. Import FieldFilter ---

router = APIRouter(prefix="/subjects", tags=["Subjects"])

@router.post("/", response_model=Subject, status_code=201)
async def create_subject(payload: Subject):
    """
    Creates a new Subject. The ID is the 'subject_id' provided.
    """
    doc_ref = db.collection("subjects").document(payload.subject_id)
    def _create():
        if doc_ref.get().exists:
            raise HTTPException(status_code=400, detail="Subject with this ID already exists")
        data = payload.to_dict()
        doc_ref.set(data)
        return data
    return await asyncio.to_thread(_create)

# --- 5. ADD THIS NEW ENDPOINT ---
@router.get("/", response_model=PaginatedResponse[Subject])
async def list_subjects(
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 100, # Increased limit for dropdowns
    start_after: Optional[str] = None
):
    """
    [All Users] Lists all subjects, with pagination.
    """
    def _get_all_sync():
        items = []
        query = db.collection("subjects").where(filter=FieldFilter("deleted", "!=", True))
        
        if start_after:
            try:
                start_doc = db.collection("subjects").document(start_after).get()
                if start_doc.exists:
                    query = query.start_after(start_doc)
            except Exception as e:
                 print(f"Warning: Invalid start_after document ID '{start_after}': {e}")

        docs = list(query.limit(limit).stream())
            
        for doc in docs:
            data = doc.to_dict()
            data["subject_id"] = doc.id
            items.append(Subject.model_validate(data))
            
        last_doc_id = docs[-1].id if docs else None
        return items, last_doc_id

    items, last_id = await asyncio.to_thread(_get_all_sync)
    return PaginatedResponse(items=items, last_doc_id=last_id)
# --- END OF NEW ENDPOINT ---

@router.get("/{subject_id}", response_model=Subject)
async def get_subject(subject_id: str):
    doc = db.collection("subjects").document(subject_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Subject not found")
    data = doc.to_dict()
    data["subject_id"] = doc.id
    return data

@router.put("/{subject_id}", response_model=Subject)
async def update_subject(subject_id: str, payload: SubjectBase):
    """
    Updates a Subject's details (like name or active_tos_id).
    """
    doc_ref = db.collection("subjects").document(subject_id)
    def _update():
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Subject not found")
        update_data = payload.model_dump(exclude_unset=True)
        doc_ref.update(update_data)
        updated = doc_ref.get().to_dict()
        updated["subject_id"] = doc_ref.id
        return updated
    return await asyncio.to_thread(_update)

# --- THIS IS THE KEY LOGIC ---
@router.post("/{subject_id}/activate_tos/{tos_id}", response_model=Subject)
async def activate_tos_version(subject_id: str, tos_id: str):
    """
    Sets a new TOS version as the active one for a Subject.
    This deactivates the old one and activates the new one.
    """
    subject_ref = db.collection("subjects").document(subject_id)
    new_tos_ref = db.collection("tos").document(tos_id)
    
    @db.transactional
    def _activate_in_transaction(transaction):
        # 1. Check if docs exist
        subject_doc = subject_ref.get(transaction=transaction)
        if not subject_doc.exists:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        new_tos_doc = new_tos_ref.get(transaction=transaction)
        if not new_tos_doc.exists:
            raise HTTPException(status_code=404, detail="New TOS not found")
        
        # 2. Get the old (current) active TOS ID
        old_tos_id = subject_doc.to_dict().get("active_tos_id")
        
        # 3. Deactivate the old TOS, if one exists
        if old_tos_id:
            old_tos_ref = db.collection("tos").document(old_tos_id)
            transaction.update(old_tos_ref, {"is_active": False})
        
        # 4. Activate the new TOS
        transaction.update(new_tos_ref, {"is_active": True})
        
        # 5. Update the Subject's 'pointer'
        transaction.update(subject_ref, {"active_tos_id": tos_id})
        
        return subject_ref.get(transaction=transaction)

    # Run the transaction
    updated_subject_doc = _activate_in_transaction(db.transaction())
    response_data = updated_subject_doc.to_dict()
    response_data["subject_id"] = updated_subject_doc.id
    return response_data