from fastapi import APIRouter, HTTPException
from database.firestore import db
from models.schema_models import Recommendation
from core.recommender import pick_recommendations_for_student


router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("/", status_code=201)
async def create_recommendation(payload: Recommendation):
    ref = db.collection("recommendations").document(payload.recommendation_id)
    if ref.get().exists:
        raise HTTPException(status_code=400, detail="Recommendation exists")
    ref.set(payload.to_dict())
    return payload.to_dict()


@router.get("/{rec_id}")
async def get_recommendation(rec_id: str):
    doc = db.collection("recommendations").document(rec_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(doc.to_dict(), recommendation_id=doc.id)


@router.get("/")
async def list_recommendations():
    return [dict(d.to_dict(), recommendation_id=d.id) for d in db.collection("recommendations").stream()]


@router.put("/{rec_id}")
async def update_recommendation(rec_id: str, payload: Recommendation):
    ref = db.collection("recommendations").document(rec_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    ref.update(payload.to_dict())
    return dict(ref.get().to_dict(), recommendation_id=rec_id)


@router.delete("/{rec_id}")
async def delete_recommendation(rec_id: str):
    db.collection("recommendations").document(rec_id).delete()
    return {"deleted": rec_id}


@router.post("/generate/{student_id}")
async def generate_recommendations(student_id: str):
    """Generate and persist recommendations for a student using rule-based recommender."""
    recs = pick_recommendations_for_student(student_id)
    if not recs:
        raise HTTPException(status_code=404, detail="No recommendations generated or student not found")
    return {"generated": len(recs), "recommendations": recs}
