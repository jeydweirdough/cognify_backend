from fastapi import APIRouter, HTTPException
from database.firestore import db
from models.schema_models import TOS

router = APIRouter(prefix="/tos", tags=["TOS"])


@router.post("/", status_code=201)
async def create_tos(payload: TOS):
    ref = db.collection("tos").document(payload.id)
    if ref.get().exists:
        raise HTTPException(status_code=400, detail="TOS exists")
    ref.set(payload.to_dict())
    return payload.to_dict()


@router.get("/{tos_id}")
async def get_tos(tos_id: str):
    doc = db.collection("tos").document(tos_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(doc.to_dict(), id=doc.id)


@router.get("/")
async def list_tos():
    return [dict(d.to_dict(), id=d.id) for d in db.collection("tos").stream()]


@router.put("/{tos_id}")
async def update_tos(tos_id: str, payload: TOS):
    ref = db.collection("tos").document(tos_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Not found")
    ref.update(payload.to_dict())
    return dict(ref.get().to_dict(), id=tos_id)


@router.delete("/{tos_id}")
async def delete_tos(tos_id: str):
    db.collection("tos").document(tos_id).delete()
    return {"deleted": tos_id}
