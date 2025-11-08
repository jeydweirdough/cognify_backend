# services/ai_content_generator.py
import httpx
import json
from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError
from database.models import GeneratedQuestion, GeneratedFlashcard

# --- Gemini API Configuration ---
API_KEY = "" 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# --- 1. NEW: Pydantic Model for a SINGLE AI Response ---
# This model will validate the *entire* package from the AI
class UnifiedLearningPackage(BaseModel):
    summary: str
    questions: List[GeneratedQuestion]
    flashcards: List[GeneratedFlashcard]
    # We can also ask the AI for the *overall* alignment
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

# --- 2. NEW: The Unified System Prompt ---
# This one prompt replaces the three old ones.
UNIFIED_GENERATION_SYSTEM_PROMPT = (
    "You are an expert academic assistant and test creator. Your task is to "
    "read the provided text from a psychology module and the provided "
    "Table of Specifications (TOS). "
    "Based *only* on the text, you must generate a complete learning package. "
    "You MUST align all content with the *most relevant* topic and "
    "Bloom's level from the TOS. "
    "Respond ONLY with a valid JSON object in the format: "
    "{"
    "  \"tos_topic_title\": \"(e.g., Theories)\", "
    "  \"aligned_bloom_level\": \"(e.g., applying)\", "
    "  \"summary\": \"...your concise summary...\", "
    "  \"questions\": ["
    "    {\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": \"A\", \"tos_topic_title\": \"(e.g., Theories)\", \"aligned_bloom_level\": \"(e.g., remembering)\"}"
    "  ], "
    "  \"flashcards\": ["
    "    {\"question\": \"What is...?\", \"answer\": \"It is...\", \"tos_topic_title\": \"(e.g., Sikolohiyang Filipino)\", \"aligned_bloom_level\": \"(e.g., remembering)\"}"
    "  ]"
    "}"
    "Generate exactly 5 quiz questions and 10 flashcards."
)

# --- 3. REFACTORED: The API call function is now generic ---
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

# --- 4. REFACTORED: This function is unchanged but good ---
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

# --- 5. NEW: The One Function to Rule Them All ---
# This one function replaces the old generate_summary, generate_quiz,
# and generate_flashcards functions.
async def generate_unified_learning_package(pdf_text: str, tos_structure: str) -> UnifiedLearningPackage:
    """
    Takes PDF text and TOS, returns a single, structured learning
    package containing a summary, quiz, and flashcards.
    """
    user_query = _create_generation_query(pdf_text, tos_structure)
    json_data = await _call_gemini_api(UNIFIED_GENERATION_SYSTEM_PROMPT, user_query)
    
    try:
        # Validate the entire package at once
        return UnifiedLearningPackage.model_validate(json_data)
    except ValidationError as e:
        print(f"AI Validation Error (Unified Package): {e}")
        raise ValueError(f"AI returned data in the wrong format for a unified package: {e}")

# --- The old generate_summary_from_text, generate_quiz_from_text, ---
# --- and generate_flashcards_from_text functions are now DELETED. ---