# services/role_service.py
from core.firebase import db
import asyncio
from google.cloud.firestore_v1.base_query import FieldFilter # Import FieldFilter

async def get_role_id_by_designation(designation: str) -> str | None:
    """
    Fetches the Firestore document ID for a role based on its designation.
    e.g., get_role_id_by_designation("student") -> "Tzc78QtZcaVbzFtpHoOL"
    """
    def _fetch_role():
        # --- FIX: Use 'filter' keyword to remove UserWarning ---
        roles_query = db.collection("roles").where(
            filter=FieldFilter("designation", "==", designation)
        ).limit(1).stream()
        
        for doc in roles_query:
            return doc.id
        return None

    role_id = await asyncio.to_thread(_fetch_role)
    return role_id