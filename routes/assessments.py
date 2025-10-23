from fastapi import APIRouter, HTTPException
from database.firestore import db
from models.schema_models import Assessment
import asyncio

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post("/", status_code=201)
async def create_assessment(payload: Assessment):
    doc_ref = db.collection("assessments").document(payload.assessment_id)
    def _create():
        if doc_ref.get().exists:
            raise HTTPException(status_code=400, detail="Assessment exists")
        doc_ref.set(payload.to_dict())
        return payload.to_dict()

    return await asyncio.to_thread(_create)


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str):
    doc = db.collection("assessments").document(assessment_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    data = doc.to_dict(); data["assessment_id"] = doc.id
    return data


@router.get("/")
async def list_assessments():
    return [dict(d.to_dict(), assessment_id=d.id) for d in db.collection("assessments").stream()]


@router.put("/{assessment_id}")
async def update_assessment(assessment_id: str, payload: Assessment):
    doc_ref = db.collection("assessments").document(assessment_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    doc_ref.update(payload.to_dict())
    updated = doc_ref.get().to_dict(); updated["assessment_id"] = assessment_id
    return updated


@router.delete("/{assessment_id}")
async def delete_assessment(assessment_id: str):
    db.collection("assessments").document(assessment_id).delete()
    return {"deleted": assessment_id}
