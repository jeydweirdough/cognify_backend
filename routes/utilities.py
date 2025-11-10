from fastapi import APIRouter, HTTPException, Depends, status
from core.security import allowed_users
from core.firebase import db
from core.config import settings  # ✅ ADD THIS
import asyncio
import random
from typing import Dict, Any, Optional
from pydantic import BaseModel
from services import profile_service
from firebase_admin import messaging
import requests
import time
from services import analytics_service

router = APIRouter(prefix="/utilities", tags=["Utilities"])

GENERIC_MESSAGES = [
    {"quote": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"quote": "You are capable of more than you know. Time to review!", "author": "Cognify"},
    {"quote": "The journey of a thousand miles begins with a single step. Let's get started.", "author": "Laozi (adapted)"},
    {"quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"quote": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"quote": "The best way to predict the future is to create it. Let's study!", "author": "Peter Drucker"},
    {"quote": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"}
]

ANALYTICS_COLLECTION = "student_analytics_reports"

class ReminderPayload(BaseModel):
    title: str = "Study Reminder!"
    body: str = "Don't forget to complete your review session for today."

class CustomMotivationPayload(BaseModel):
    quote: str
    author: Optional[str] = "Your Faculty Advisor"


def _call_gemini_api_sync(report_data: dict, retry_count=3) -> str:
    """
    SYNCHRONOUS function that calls the Gemini API.
    Designed to be run in a thread.
    """
    try:
        prob = report_data.get("prediction", {}).get("pass_probability", 75.0)
        activities = report_data.get("summary", {}).get("total_activities", 10)
        bloom = report_data.get("performance_by_bloom", {})
        
        weakest_area = ""
        if bloom:
            weakest_area = min(bloom.items(), key=lambda item: item[1])[0]

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

        # ✅ FIX: Use environment variable
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("ERROR: GEMINI_API_KEY not set. Cannot generate motivation.")
            return "Keep pushing forward. Every bit of effort counts!"
        
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
        }

        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if text:
            print(f"Generated ON-DEMAND AI quote.")
            return text.strip().strip('"')

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429 and retry_count > 0:
            print(f"Rate limited. Retrying in {6 - retry_count}s...")
            time.sleep(6 - retry_count)
            return _call_gemini_api_sync(report_data, retry_count - 1)
        print(f"Error generating AI quote (HTTPError): {e}")
    except Exception as e:
        print(f"Error generating AI quote: {e}")

    return "Keep pushing forward. Every bit of effort counts!"


@router.post("/motivation/generate/{user_id}", response_model=Dict[str, str])
async def generate_new_motivational_message(
    user_id: str,
    decoded=Depends(allowed_users(["student"]))
):
    """[Student] Generates a new, on-demand AI motivational quote"""
    
    def _generate_and_save_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report_data = loop.run_until_complete(analytics_service.get_live_analytics(user_id))
        finally:
            loop.close()
        
        if not report_data:
            raise HTTPException(status_code=404, detail="No analytics data found. Cannot generate quote.")
        
        report_data["student_id"] = user_id

        new_quote = _call_gemini_api_sync(report_data)

        doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
        doc_ref.set({
            "ai_motivation": new_quote,
            "custom_motivation": None
        }, merge=True)
        
        return {
            "quote": new_quote,
            "author": "Cognify AI Mentor"
        }

    try:
        return await asyncio.to_thread(_generate_and_save_sync)
    except Exception as e:
        print(f"Error in on-demand generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate new motivation.")


@router.get("/motivation/{user_id}", response_model=Dict[str, str])
async def get_motivational_message(
    user_id: str,
    decoded=Depends(allowed_users(["student", "faculty_member", "admin"]))
):
    """[All Users] Fetches the currently saved personalized quote"""
    
    def _get_ai_quote_sync():
        try:
            doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return random.choice(GENERIC_MESSAGES)
            
            data = doc.to_dict()
            
            custom_quote = data.get("custom_motivation")
            if custom_quote and custom_quote.get("quote"):
                return {
                    "quote": custom_quote.get("quote"),
                    "author": custom_quote.get("author", "Your Faculty Advisor")
                }

            quote = data.get("ai_motivation")
            
            if not quote:
                return random.choice(GENERIC_MESSAGES)
            
            return {
                "quote": quote,
                "author": "Cognify AI Mentor"
            }

        except Exception as e:
            print(f"Error fetching AI quote: {e}")
            return random.choice(GENERIC_MESSAGES)

    return await asyncio.to_thread(_get_ai_quote_sync)


@router.put("/motivation/{user_id}", status_code=status.HTTP_200_OK)
async def set_custom_motivation(
    user_id: str,
    payload: CustomMotivationPayload,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Admin/Faculty] Sets a custom motivational message for a student"""
    def _set_motivation_sync():
        try:
            doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
            doc_ref.set({
                "custom_motivation": payload.model_dump()
            }, merge=True)
            return {"message": "Custom motivation set successfully."}
        except Exception as e:
            print(f"Error setting custom motivation: {e}")
            raise HTTPException(status_code=500, detail="Failed to set custom motivation.")
    
    return await asyncio.to_thread(_set_motivation_sync)


@router.delete("/motivation/{user_id}", status_code=status.HTTP_200_OK)
async def clear_custom_motivation(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Admin/Faculty] Clears a custom motivation"""
    def _clear_motivation_sync():
        try:
            doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
            doc_ref.update({"custom_motivation": None})
            return {"message": "Custom motivation cleared successfully."}
        except Exception as e:
            print(f"Error clearing custom motivation: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear custom motivation.")
    
    return await asyncio.to_thread(_clear_motivation_sync)


@router.post("/send_reminder/{user_id}", status_code=status.HTTP_200_OK)
async def send_study_reminder(
    user_id: str,
    payload: ReminderPayload,
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """[Admin/Faculty] Sends a push notification study reminder"""
    
    profile = await profile_service.get(user_id)
    
    if not profile:
        print(f"Error: Profile not found for user {user_id}")
        raise HTTPException(status_code=404, detail="User profile not found.")

    token = profile.fcm_token
    if not token:
        print(f"Error: No FCM token registered for user {user_id}")
        raise HTTPException(status_code=400, detail="User does not have a registered device token.")

    def _send_notification_sync():
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=payload.title,
                    body=payload.body,
                ),
                token=token,
            )
            response = messaging.send(message)
            print(f"Successfully sent message to {user_id}: {response}")
            return response
        except Exception as e:
            print(f"Error sending push notification to {user_id}: {e}")
            return None

    await asyncio.to_thread(_send_notification_sync)
    
    return {"message": "Reminder sent successfully."}