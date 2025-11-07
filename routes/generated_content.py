# routes/generated_content.py
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
import asyncio
import json
from database.models import (
    PaginatedResponse, Module, Subject, TOS,
    GeneratedSummary, GeneratedSummaryBase,
    GeneratedQuiz, GeneratedQuizBase,
    GeneratedFlashcards, GeneratedFlashcardsBase
)
from services import (
    module_service, 
    generated_summary_service, 
    generated_quiz_service,
    generated_flashcards_service,
    tos_service  # --- NEW: Need this to get TOS ---
)
from services.ai_content_generator import (
    generate_summary_from_text, 
    generate_quiz_from_text,
    generate_flashcards_from_text
)
from core.security import allowed_users
from core.firebase import db # --- NEW: Need this for subject ---
import httpx
import fitz  # PyMuPDF
import io

router = APIRouter(prefix="/generate", tags=["AI Generated Content"])

# --- NEW: Helper function to fetch and simplify the Active TOS ---
async def _fetch_and_simplify_active_tos(subject_id: str) -> str:
    """
    Fetches the active TOS for a subject and simplifies it into a text
    blob for the AI prompt.
    """
    # 1. Fetch the Subject document
    def _get_subject():
        doc = db.collection("subjects").document(subject_id).get()
        if not doc.exists: return None
        data = doc.to_dict()
        data["subject_id"] = doc.id
        return Subject.model_validate(data)
    
    subject = await asyncio.to_thread(_get_subject)

    # 2. Determine which TOS to use
    active_tos: Optional[TOS] = None
    if subject and subject.active_tos_id:
        active_tos = await tos_service.get(subject.active_tos_id)
    
    if not active_tos:
        # Fallback: Try to find *any* TOS for the subject
        all_tos_items, _ = await tos_service.where("subject_id", "==", subject_id, limit=1)
        if all_tos_items:
            active_tos = all_tos_items[0]
        else:
            # No TOS found at all
            print(f"Warning: No TOS found for subject {subject_id}. AI alignment will be skipped.")
            return "{\"error\": \"No Table of Specifications provided.\"}"

    # 3. Simplify the TOS for the AI prompt
    try:
        simplified_content = []
        if active_tos.content:
            for section in active_tos.content:
                sub_purposes = []
                if section.sub_content:
                    for sub in section.sub_content:
                        sub_purposes.append({
                            "purpose": sub.purpose,
                            "blooms_taxonomy": [b.root for b in sub.blooms_taxonomy] if sub.blooms_taxonomy else []
                        })
                simplified_content.append({
                    "title": section.title,
                    "sub_content": sub_purposes
                })
        
        simplified_tos = {
            "subject_name": active_tos.subject_name,
            "content": simplified_content
        }
        return json.dumps(simplified_tos, indent=2)
    except Exception as e:
        print(f"Error simplifying TOS: {e}")
        return "{\"error\": \"Could not parse Table of Specifications.\"}"

# --- Helper function to process the PDF (UPDATED) ---
async def _process_pdf_and_generate(module_id: str):
    """
    Background task to download, read, fetch TOS, and generate content.
    """
    print(f"Starting background generation for module: {module_id}")
    try:
        module = await module_service.get(module_id)
        if not module or not module.material_url or not module.subject_id:
            print(f"Error: Module {module_id} not found or missing URL/Subject ID.")
            return

        # 1. Fetch and simplify the active TOS (NEW)
        tos_structure_str = await _fetch_and_simplify_active_tos(module.subject_id)

        # 2. Download the PDF file from the public URL
        async with httpx.AsyncClient() as client:
            response = await client.get(module.material_url, timeout=30.0)
            response.raise_for_status()
            pdf_data = io.BytesIO(response.content)

        # 3. Extract text using PyMuPDF (fitz)
        full_text = ""
        with fitz.open(stream=pdf_data, filetype="pdf") as doc:
            for page in doc:
                full_text += page.get_text() + "\n"
        
        char_count = len(full_text)
        if char_count < 100:
            print(f"Error: PDF for module {module_id} contains no readable text.")
            return
        
        print(f"Successfully extracted {char_count} chars from {module.material_url}")

        # 4. Generate Summary (Updated)
        try:
            summary_resp = await generate_summary_from_text(full_text, tos_structure_str)
            summary_payload = GeneratedSummaryBase(
                module_id=module_id,
                subject_id=module.subject_id,
                summary_text=summary_resp.summary,
                source_url=module.material_url,
                source_char_count=char_count,
                tos_topic_title=summary_resp.tos_topic_title,
                aligned_bloom_level=summary_resp.aligned_bloom_level
            )
            created_summary = await generated_summary_service.create(summary_payload)
            await module_service.update(module_id, {"generated_summary_id": created_summary.id})
            print(f"Successfully generated summary {created_summary.id} for module {module_id}")
        except Exception as e:
            print(f"Failed to generate summary for {module_id}: {e}")

        # 5. Generate Quiz (Updated)
        try:
            quiz_resp = await generate_quiz_from_text(full_text, tos_structure_str)
            quiz_payload = GeneratedQuizBase(
                module_id=module_id,
                subject_id=module.subject_id,
                questions=quiz_resp.questions,
                source_url=module.material_url,
                source_char_count=char_count,
                tos_topic_title=quiz_resp.tos_topic_title,
                aligned_bloom_level=quiz_resp.aligned_bloom_level
            )
            created_quiz = await generated_quiz_service.create(quiz_payload)
            await module_service.update(module_id, {"generated_quiz_id": created_quiz.id})
            print(f"Successfully generated quiz {created_quiz.id} for module {module_id}")
        except Exception as e:
            print(f"Failed to generate quiz for {module_id}: {e}")

        # 6. Generate Flashcards (Updated)
        try:
            flashcards_resp = await generate_flashcards_from_text(full_text, tos_structure_str)
            flashcards_payload = GeneratedFlashcardsBase(
                module_id=module_id,
                subject_id=module.subject_id,
                flashcards=flashcards_resp.flashcards,
                source_url=module.material_url,
                source_char_count=char_count,
                tos_topic_title=flashcards_resp.tos_topic_title,
                aligned_bloom_level=flashcards_resp.aligned_bloom_level
            )
            created_flashcards = await generated_flashcards_service.create(flashcards_payload)
            await module_service.update(module_id, {"generated_flashcards_id": created_flashcards.id})
            print(f"Successfully generated flashcards {created_flashcards.id} for module {module_id}")
        except Exception as e:
            print(f"Failed to generate flashcards for {module_id}: {e}")
            
    except httpx.HTTPStatusError as e:
        print(f"Failed to download PDF {module.material_url}: {e}")
    except Exception as e:
        print(f"Unhandled error in background task for {module_id}: {e}")

# --- API Endpoints ---

@router.post("/from_module/{module_id}", status_code=status.HTTP_202_ACCEPTED)
async def generate_content_from_module(
    module_id: str,
    background_tasks: BackgroundTasks,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Triggers a background task to read a module's
    PDF, align it with the active TOS, and generate all AI content.
    """
    # Verify module exists before queueing
    module = await module_service.get(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    background_tasks.add_task(_process_pdf_and_generate, module_id)
    
    return {"message": "AI content generation has been queued. This may take a few minutes."}

@router.get("/generated_summaries/for_module/{module_id}", response_model=PaginatedResponse[GeneratedSummary])
async def get_generated_summaries_for_module(
    module_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 10,
    start_after: Optional[str] = None
):
    """
    [All] Gets any AI-generated summaries for a specific module.
    """
    items, last_id = await generated_summary_service.where(
        "module_id", "==", module_id, 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/generated_quizzes/for_module/{module_id}", response_model=PaginatedResponse[GeneratedQuiz])
async def get_generated_quizzes_for_module(
    module_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 10,
    start_after: Optional[str] = None
):
    """
    [All] Gets any AI-generated quizzes for a specific module.
    """
    items, last_id = await generated_quiz_service.where(
        "module_id", "==", module_id, 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)

@router.get("/generated_flashcards/for_module/{module_id}", response_model=PaginatedResponse[GeneratedFlashcards])
async def get_generated_flashcards_for_module(
    module_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"])),
    limit: int = 10,
    start_after: Optional[str] = None
):
    """
    [All] Gets any AI-generated flashcards for a specific module.
    """
    items, last_id = await generated_flashcards_service.where(
        "module_id", "==", module_id, 
        limit=limit, 
        start_after=start_after
    )
    return PaginatedResponse(items=items, last_doc_id=last_id)