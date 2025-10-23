from fastapi import APIRouter, HTTPException
from database.firestore import db
from models.schema_models import Quiz

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.post("/", status_code=201)
async def create_quiz(payload: Quiz):
    ref = db.collection("quizzes").document(payload.quiz_id)
    if ref.get().exists:
        raise HTTPException(status_code=400, detail="Quiz exists")
    ref.set(payload.to_dict())
    return payload.to_dict()


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str):
    doc = db.collection("quizzes").document(quiz_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(doc.to_dict(), quiz_id=doc.id)


@router.get("/")
async def list_quizzes():
    return [dict(d.to_dict(), quiz_id=d.id) for d in db.collection("quizzes").stream()]


@router.put("/{quiz_id}")
async def update_quiz(quiz_id: str, payload: Quiz):
    ref = db.collection("quizzes").document(quiz_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    ref.update(payload.to_dict())
    return dict(ref.get().to_dict(), quiz_id=quiz_id)


@router.delete("/{quiz_id}")
async def delete_quiz(quiz_id: str):
    db.collection("quizzes").document(quiz_id).delete()
    return {"deleted": quiz_id}
