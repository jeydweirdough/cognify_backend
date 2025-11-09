# utils/status_utils.py
import asyncio
from datetime import datetime, timedelta
from core.firebase import db
from google.cloud.firestore_v1.base_query import FieldFilter

async def update_user_status(uid: str, status: str):
    """Updates the user's status and last_seen time in Firestore."""
    def _update_db():
        try:
            user_ref = db.collection("user_profiles").document(uid)
            update_data = {
                "status": status,
                "last_seen": datetime.utcnow()
            }
            # Use set with merge=True to create/update the fields
            user_ref.set(update_data, merge=True) 
            print(f"Updated status for {uid} to {status}")
        except Exception as e:
            print(f"Error updating status for {uid}: {e}")
    
    await asyncio.to_thread(_update_db)

async def check_offline_users():
    """
    (Scheduled Task) Mark users as offline if they haven't been seen.
    NOTE: This should be run by a scheduler, not by user APIs.
    """
    def _check_db():
        try:
            users = db.collection("user_profiles").where(
                filter=FieldFilter("status", "in", ["online", "busy"])
            ).stream()
            
            # Set cutoff to 5 minutes for a scheduled task
            cutoff = datetime.utcnow() - timedelta(minutes=5) 
            
            for user in users:
                data = user.to_dict()
                last_seen = data.get("last_seen")
                
                if hasattr(last_seen, "timestamp"):
                    last_seen = datetime.fromtimestamp(last_seen.timestamp())
                
                if last_seen and last_seen < cutoff:
                    user.reference.update({
                        "status": "offline",
                        "last_seen": datetime.utcnow()
                    })
                    print(f"Marked {user.id} as offline (no recent activity)")
                    
        except Exception as e:
            print(f"Error checking offline status: {e}")
    
    await asyncio.to_thread(_check_db)