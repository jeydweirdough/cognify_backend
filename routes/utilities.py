# jeydweirdough/cognify_backend/cognify_backend-2c9bd547ece812c69eb03e791dc56811f9fbe7c8/routes/utilities.py

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

# --- NEW: Import 'requests' for live API calls ---
import requests
import time

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


# --- NEW: Helper function to generate AI quote on-demand ---
def _call_gemini_api_sync(report_data: dict, retry_count=3) -> str:
    """
    This is a SYNCHRONOUS, BLOCKING function that calls the Gemini API.
    It's designed to be run in a thread.
    """
    try:
        # 1. Extract data for the prompt
        prob = report_data.get("prediction", {}).get("pass_probability", 75.0)
        activities = report_data.get("summary", {}).get("total_activities", 10)
        bloom = report_data.get("performance_by_bloom", {})
        
        weakest_area = ""
        if bloom:
            weakest_area = min(bloom.items(), key=lambda item: item[1])[0]

        # 2. Create the prompt
        system_prompt = (
            "You are an encouraging and wise mentor for a psychology student "
            "preparing for their licensure exam. Your role is to provide a single, "
            "short (1-2 sentence) motivational quote. Be specific, positive, and forward-looking. "
            "Do not use markdown."
        )
        
        user_query = (
            f"My student's profile: "
            f"Pass Probability: {prob}%. "
            f"Total Activities: {activities}. "
            f"Weakest Area: '{weakest_area}'. "
            "Write a single, new, *different* motivational quote for them."
        )

        # 3. Call the Gemini API
        api_key = "" # This is handled by the platform
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
        
        payload = {
            "contents": [{ "parts": [{ "text": user_query }] }],
            "systemInstruction": { "parts": [{ "text": system_prompt }] },
        }

        # 4. Make the request using 'requests' (synchronous)
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status() # Raise an error for bad responses
        
        result = response.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if text:
            print(f"Generated ON-DEMAND AI quote for {report_data.get('student_id')}.")
            return text.strip().strip('"')

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429 and retry_count > 0: # Handle rate limiting
            print(f"Rate limited. Retrying in {6 - retry_count}s...")
            time.sleep(6 - retry_count) # Exponential backoff
            return _call_gemini_api_sync(report_data, retry_count - 1)
        print(f"Error generating AI quote (HTTPError): {e}")
    except Exception as e:
        print(f"Error generating AI quote: {e}")

    # --- Fallback Logic (if API fails) ---
    return "Keep pushing forward. Every bit of effort counts!"


# --- NEW: On-demand POST endpoint to generate a fresh quote ---
@router.post("/motivation/generate/{user_id}", response_model=Dict[str, str])
async def generate_new_motivational_message(
    user_id: str,
    decoded=Depends(allowed_users(["student"])) # Only students can generate for themselves
):
    """
    [Student] Generates a new, on-demand AI motivational quote.
    This is an "expensive" call and should be used sparingly
    (e.g., via a button click).
    """
    
    def _generate_and_save_sync():
        # 1. Fetch the student's *existing* analytics report (1 read)
        doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analytics report not found. Cannot generate quote.")
        
        report_data = doc.to_dict()
        report_data["student_id"] = user_id # Ensure ID is present

        # 2. Call the blocking Gemini API function
        new_quote = _call_gemini_api_sync(report_data)

        # 3. Save the new quote back to the document
        # This also clears any custom faculty quote, as the student
        # has requested a new one.
        doc_ref.update({
            "ai_motivation": new_quote,
            "custom_motivation": None
        })
        
        return {
            "quote": new_quote,
            "author": "Cognify AI Mentor"
        }

    try:
        # Run the entire process in a thread to avoid blocking the API
        return await asyncio.to_thread(_generate_and_save_sync)
    except Exception as e:
        print(f"Error in on-demand generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate new motivation.")


# --- This endpoint is for READING the saved quote (fast) ---
@router.get("/motivation/{user_id}", response_model=Dict[str, str])
async def get_motivational_message(
    user_id: str, # Added user_id as a path parameter
    decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))
):
    """
    [All Users] Fetches the *currently saved* personalized quote.
    
    This is fast and efficient (1 read). It prioritizes:
    1. A custom quote from faculty (set via PUT).
    2. The daily or on-demand AI-generated quote.
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


# --- This endpoint is for FACULTY to override the quote ---
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
            
            # --- THIS IS THE FIX ---
            # Use .set(..., merge=True) to create or update the doc
            doc_ref.set({
                "custom_motivation": payload.model_dump()
            }, merge=True)
            # --- END FIX ---
            
            return {"message": "Custom motivation set successfully."}
        except Exception as e:
            print(f"Error setting custom motivation: {e}")
            raise HTTPException(status_code=500, detail="Failed to set custom motivation.")
    
    return await asyncio.to_thread(_set_motivation_sync)


# --- This endpoint is for FACULTY to clear their override ---
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


# --- This endpoint sends a push notification ---
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