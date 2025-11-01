# routes/utilities.py
from fastapi import APIRouter, HTTPException, Depends, status
from core.security import allowed_users
from core.firebase import db
import asyncio
import random
from typing import Dict, Any, Optional
from pydantic import BaseModel
from services import profile_service

# --- NEW: Import Firebase Admin Messaging ---
from firebase_admin import messaging

router = APIRouter(prefix="/utilities", tags=["Utilities"])

# --- UPDATED: Added more fallback messages ---
GENERIC_MESSAGES = [
    {
        "quote": "It always seems impossible until it's done.",
        "author": "Nelson Mandela"
    },
    {
        "quote": "You are capable of more than you know. Time to review!",
        "author": "Cognify"
    },
    {
        "quote": "The journey of a thousand miles begins with a single step. Let's get started.",
        "author": "Laozi (adapted)"
    },
    {
        "quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "author": "Winston Churchill"
    },
    {
        "quote": "Believe you can and you're halfway there.",
        "author": "Theodore Roosevelt"
    },
    {
        "quote": "The best way to predict the future is to create it. Let's study!",
        "author": "Peter Drucker"
    },
    {
        "quote": "Don't watch the clock; do what it does. Keep going.",
        "author": "Sam Levenson"
    }
]


ANALYTICS_COLLECTION = "student_analytics_reports"


class ReminderPayload(BaseModel):
    title: str = "Study Reminder!"
    body: str = "Don't forget to complete your review session for today."

# --- NEW: Pydantic model for the custom motivation payload ---
class CustomMotivationPayload(BaseModel):
    quote: str
    author: Optional[str] = "Your Faculty Advisor"


# --- UPDATED: Route changed to /motivation/{user_id} ---
@router.get("/motivation/{user_id}", response_model=Dict[str, str])
async def get_motivational_message(
    user_id: str, # Added user_id as a path parameter
    decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))
):
    """
    [All Users] Fetches the personalized motivational quote.
    
    This is fast and efficient (1 read). It prioritizes:
    1. A custom quote from faculty.
    2. The daily AI-generated quote.
    3. A generic fallback quote.
    """
    
    # user_id now comes from the function argument, not the decoded token
    
    def _get_ai_quote_sync():
        try:
            # 1. Fetch the student's analytics report (1 read)
            doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                # Fallback for new users
                return random.choice(GENERIC_MESSAGES)
            
            data = doc.to_dict()
            
            # --- NEW LOGIC ---
            # 1. Check for a custom, overriding message first.
            custom_quote = data.get("custom_motivation")
            if custom_quote and custom_quote.get("quote"):
                return {
                    "quote": custom_quote.get("quote"),
                    "author": custom_quote.get("author", "Your Faculty Advisor")
                }

            # 2. Get the pre-generated AI quote
            quote = data.get("ai_motivation")
            
            if not quote:
                # Fallback if the quote is missing
                return random.choice(GENERIC_MESSAGES)
            
            # 3. Return the AI-generated quote
            return {
                "quote": quote,
                "author": "Cognify AI Mentor"
            }

        except Exception as e:
            print(f"Error fetching AI quote: {e}")
            return random.choice(GENERIC_MESSAGES)

    # Run the synchronous DB call in a thread to avoid blocking
    return await asyncio.to_thread(_get_ai_quote_sync)


# --- NEW: Endpoint to set a custom motivation for a student ---
@router.put("/motivation/{user_id}", status_code=status.HTTP_200_OK)
async def set_custom_motivation(
    user_id: str,
    payload: CustomMotivationPayload,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Sets a custom motivational message for a student,
    overriding the daily AI-generated one.
    """
    def _set_motivation_sync():
        try:
            doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
            
            # Use .update() to set the new field
            doc_ref.update({
                "custom_motivation": payload.model_dump()
            })
            return {"message": "Custom motivation set successfully."}
        except Exception as e:
            print(f"Error setting custom motivation: {e}")
            # Check if the doc doesn't exist
            if "Not found" in str(e):
                raise HTTPException(status_code=404, detail="Student analytics report not found. Cannot set motivation.")
            raise HTTPException(status_code=500, detail="Failed to set custom motivation.")
    
    return await asyncio.to_thread(_set_motivation_sync)


# --- NEW: Endpoint to clear the custom motivation ---
@router.delete("/motivation/{user_id}", status_code=status.HTTP_200_OK)
async def clear_custom_motivation(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Clears a custom motivation, reverting to the
    daily AI-generated one.
    """
    def _clear_motivation_sync():
        try:
            doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
            
            # Use .update() to set the field to None (or delete)
            doc_ref.update({
                "custom_motivation": None
            })
            return {"message": "Custom motivation cleared successfully."}
        except Exception as e:
            print(f"Error clearing custom motivation: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear custom motivation.")
    
    return await asyncio.to_thread(_clear_motivation_sync)


# --- UPDATED: Endpoint logic is now cleaner and more robust ---
@router.post("/send_reminder/{user_id}", status_code=status.HTTP_200_OK)
async def send_study_reminder(
    user_id: str,
    payload: ReminderPayload,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Sends a push notification study reminder
    to a specific user.
    """
    
    # 1. Get the user's profile (this is now async)
    profile = await profile_service.get(user_id)
    
    if not profile:
        print(f"Error: Profile not found for user {user_id}")
        raise HTTPException(status_code=404, detail="User profile not found.")

    # 2. Check if they have a device token
    token = profile.fcm_token
    if not token:
        print(f"Error: No FCM token registered for user {user_id}")
        raise HTTPException(status_code=400, detail="User does not have a registered device token.")

    # 3. This is a synchronous, blocking I/O call
    # We must run it in a thread to avoid blocking the server
    def _send_notification_sync():
        try:
            # 3. Construct the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=payload.title,
                    body=payload.body,
                ),
                token=token,
            )
            # 4. Send the message
            response = messaging.send(message)
            print(f"Successfully sent message to {user_id}: {response}")
            return response
        except Exception as e:
            print(f"Error sending push notification to {user_id}: {e}")
            return None

    # Run the blocking 'send' operation in a thread
    await asyncio.to_thread(_send_notification_sync)
    
    return {"message": "Reminder sent to processing queue."}

