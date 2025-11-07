# services/ai_content_generator.py
import httpx
import json
from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError
from database.models import GeneratedQuestion, GeneratedFlashcard

# --- Gemini API Configuration ---
API_KEY = "" 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# --- Pydantic Models for AI Response Validation (Updated) ---
class GeneratedSummaryResponse(BaseModel):
    summary: str
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

class GeneratedQuizResponse(BaseModel):
    questions: List[GeneratedQuestion]
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None
    
class GeneratedFlashcardsResponse(BaseModel):
    flashcards: List[GeneratedFlashcard]
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

# --- System Prompts (UPDATED for TOS Alignment) ---
SUMMARY_SYSTEM_PROMPT = (
    "You are an expert academic assistant. Your task is to read the provided text "
    "from a psychology module and generate a concise, professional summary of the key "
    "concepts, definitions, and theories. Use bullet points for clarity. "
    "**You MUST also align this summary with the *most relevant* topic from the provided Table of Specifications (TOS).** "
    "Respond ONLY with a valid JSON object in the format: "
    "{\"summary\": \"...your summary...\", \"tos_topic_title\": \"(e.g., Theories)\", \"aligned_bloom_level\": \"(e.g., understanding)\"}"
)

QUIZ_SYSTEM_PROMPT = (
    "You are an expert psychology test creator. Your task is to read the provided text "
    "from a psychology module and generate exactly 5 multiple-choice questions based *only* "
    "on the text. "
    "**Each question MUST be aligned with a *specific topic* and *Bloom's level* from the provided Table of Specifications (TOS).** "
    "The *overall* quiz should also align with the *most relevant* topic. "
    "Respond ONLY with a valid JSON object in the format: "
    "{\"tos_topic_title\": \"(e.g., Theories)\", \"aligned_bloom_level\": \"(e.g., applying)\", "
    "\"questions\": [{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": \"A\", \"tos_topic_title\": \"(e.g., Theories)\", \"aligned_bloom_level\": \"(e.g., remembering)\"}]}"
)

FLASHCARDS_SYSTEM_PROMPT = (
    "You are an expert learning assistant. Your task is to read the provided text "
    "from a psychology module and generate 10 key flashcards. Each flashcard must be a "
    "clear question and a concise answer based *only* on the text. "
    "**Each flashcard MUST be aligned with a *specific topic* and *Bloom's level* from the provided Table of Specifications (TOS).** "
    "The *overall* set should also align with the *most relevant* topic. "
    "Respond ONLY with a valid JSON object in the format: "
    "{\"tos_topic_title\": \"(e.g., Sikolohiyang Filipino)\", \"aligned_bloom_level\": \"(e.g., remembering)\", "
    "\"flashcards\": [{\"question\": \"What is...?\", \"answer\": \"It is...\", \"tos_topic_title\": \"(e.g., Sikolohiyang Filipino)\", \"aligned_bloom_level\": \"(e.g., remembering)\"}]}"
)

async def _call_gemini_api(system_prompt: str, user_query: str) -> Dict[str, Any]:
    """
    Helper function to call the Gemini API.
    The user_query should contain BOTH the PDF text and the TOS structure.
    """
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload, timeout=60.0)
            response.raise_for_status()
            
            result = response.json()
            text_response = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            if not text_response:
                raise ValueError("AI returned an empty response.")
            
            clean_text = text_response.strip().removeprefix("```json").removesuffix("```").strip()
            
            return json.loads(clean_text)
            
        except json.JSONDecodeError as e:
            print(f"AI Error: Failed to decode JSON. Raw response: {clean_text}")
            raise ValueError(f"AI returned invalid JSON: {e}")
        except httpx.HTTPStatusError as e:
            print(f"AI Error: HTTP error {e.response.status_code}: {e.response.text}")
            raise ValueError(f"AI API request failed: {e.response.status_code}")
        except Exception as e:
            print(f"AI Error: Unexpected error: {e}")
            raise ValueError(f"An unexpected error occurred with the AI service: {e}")

def _create_generation_query(pdf_text: str, tos_structure: str) -> str:
    """Combines PDF text and TOS structure into a single query for the AI."""
    # Truncate text to avoid exceeding token limits
    max_pdf_chars = 14000
    max_tos_chars = 1000
    
    if len(pdf_text) > max_pdf_chars:
        pdf_text = pdf_text[:max_pdf_chars]
        print(f"Warning: Truncating input PDF text to {max_pdf_chars} chars.")
        
    if len(tos_structure) > max_tos_chars:
        tos_structure = tos_structure[:max_tos_chars]
        print(f"Warning: Truncating input TOS text to {max_tos_chars} chars.")

    return f"""
    Here is the Table of Specifications (TOS) for this subject. Use this for alignment:
    ---[TOS START]---
    {tos_structure}
    ---[TOS END]---
    
    Here is the text from the module. Generate your content based *only* on this text:
    ---[MODULE TEXT START]---
    {pdf_text}
    ---[MODULE TEXT END]---
    """

async def generate_summary_from_text(pdf_text: str, tos_structure: str) -> GeneratedSummaryResponse:
    """
    Takes PDF text and TOS, returns a structured, TOS-aligned summary.
    """
    user_query = _create_generation_query(pdf_text, tos_structure)
    json_data = await _call_gemini_api(SUMMARY_SYSTEM_PROMPT, user_query)
    
    try:
        return GeneratedSummaryResponse.model_validate(json_data)
    except ValidationError as e:
        print(f"AI Validation Error (Summary): {e}")
        raise ValueError(f"AI returned data in the wrong format for a summary: {e}")

async def generate_quiz_from_text(pdf_text: str, tos_structure: str) -> GeneratedQuizResponse:
    """
    Takes PDF text and TOS, returns a structured, TOS-aligned quiz.
    """
    user_query = _create_generation_query(pdf_text, tos_structure)
    json_data = await _call_gemini_api(QUIZ_SYSTEM_PROMPT, user_query)
    
    try:
        return GeneratedQuizResponse.model_validate(json_data)
    except ValidationError as e:
        print(f"AI Validation Error (Quiz): {e}")
        raise ValueError(f"AI returned data in the wrong format for a quiz: {e}")

async def generate_flashcards_from_text(pdf_text: str, tos_structure: str) -> GeneratedFlashcardsResponse:
    """
    Takes PDF text and TOS, returns structured, TOS-aligned flashcards.
    """
    user_query = _create_generation_query(pdf_text, tos_structure)
    json_data = await _call_gemini_api(FLASHCARDS_SYSTEM_PROMPT, user_query)
    
    try:
        return GeneratedFlashcardsResponse.model_validate(json_data)
    except ValidationError as e:
        print(f"AI Validation Error (Flashcards): {e}")
        raise ValueError(f"AI returned data in the wrong format for flashcards: {e}")