from fastapi import APIRouter, HTTPException
from database.firestore import db
from models.schema_models import Student

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/", status_code=201)
async def create_student(payload: Student):
    ref = db.collection("students").document(payload.student_id)
    if ref.get().exists:
        raise HTTPException(status_code=400, detail="Student exists")
    ref.set(payload.to_dict())
    return payload.to_dict()


@router.get("/{student_id}")
async def get_student(student_id: str):
    doc = db.collection("students").document(student_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(doc.to_dict(), student_id=doc.id)


@router.get("/")
async def list_students():
    return [dict(d.to_dict(), student_id=d.id) for d in db.collection("students").stream()]


@router.put("/{student_id}")
async def update_student(student_id: str, payload: Student):
    ref = db.collection("students").document(student_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    ref.update(payload.to_dict())
    return dict(ref.get().to_dict(), student_id=student_id)


@router.delete("/{student_id}")
async def delete_student(student_id: str):
    db.collection("students").document(student_id).delete()
    return {"deleted": student_id}
