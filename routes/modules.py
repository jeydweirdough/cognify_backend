from fastapi import APIRouter, HTTPException
from database.firestore import db
from models.schema_models import Module

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.post("/", status_code=201)
async def create_module(payload: Module):
    ref = db.collection("modules").document(payload.module_id)
    if ref.get().exists:
        raise HTTPException(status_code=400, detail="Module exists")
    ref.set(payload.to_dict())
    return payload.to_dict()


@router.get("/{module_id}")
async def get_module(module_id: str):
    doc = db.collection("modules").document(module_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(doc.to_dict(), module_id=doc.id)


@router.get("/")
async def list_modules():
    return [dict(d.to_dict(), module_id=d.id) for d in db.collection("modules").stream()]


@router.put("/{module_id}")
async def update_module(module_id: str, payload: Module):
    ref = db.collection("modules").document(module_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    ref.update(payload.to_dict())
    return dict(ref.get().to_dict(), module_id=module_id)


@router.delete("/{module_id}")
async def delete_module(module_id: str):
    db.collection("modules").document(module_id).delete()
    return {"deleted": module_id}
