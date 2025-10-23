from fastapi import APIRouter, HTTPException
from typing import List
from database.firestore import db
from models.schema_models import Activity
import asyncio

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.post("/", status_code=201)
async def create_activity(payload: Activity):
    doc_ref = db.collection("activities").document(payload.activity_id)
    data = payload.to_dict()

    def _create():
        if doc_ref.get().exists:
            raise HTTPException(status_code=400, detail="Activity already exists")
        doc_ref.set(data)
        return data

    return await asyncio.to_thread(_create)


@router.get("/{activity_id}")
async def get_activity(activity_id: str):
    doc = db.collection("activities").document(activity_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    data = doc.to_dict()
    data["activity_id"] = doc.id
    return data


@router.get("/")
async def list_activities():
    docs = db.collection("activities").stream()
    return [dict(doc.to_dict(), activity_id=doc.id) for doc in docs]


@router.put("/{activity_id}")
async def update_activity(activity_id: str, payload: Activity):
    doc_ref = db.collection("activities").document(activity_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    doc_ref.update(payload.to_dict())
    updated = doc_ref.get().to_dict()
    updated["activity_id"] = activity_id
    return updated


@router.delete("/{activity_id}")
async def delete_activity(activity_id: str):
    doc_ref = db.collection("activities").document(activity_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    doc_ref.delete()
    return {"deleted": activity_id}
