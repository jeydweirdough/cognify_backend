import httpx
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError
from database.models import GeneratedQuestion, GeneratedFlashcard
from core.config import settings

# Gemini API Configuration
API_KEY = settings.GEMINI_API_KEY

if not API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not configured. AI content generation will be disabled.")
    API_URL = None
else:
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={API_KEY}"

# Unified Learning Package Model
class UnifiedLearningPackage(BaseModel):
    summary: str
    questions: List[GeneratedQuestion]
    flashcards: List[GeneratedFlashcard]
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

# System Prompt
UNIFIED_GENERATION_SYSTEM_PROMPT = (
    "You are an expert academic assistant and test creator for psychology education. "
    "Your task is to read the provided text from a psychology module and the provided "
    "Table of Specifications (TOS). "
    "Based ONLY on the text, you must generate a complete learning package. "
    "You MUST align all content with the most relevant topic and "
    "Bloom's level from the TOS. "
    "Respond ONLY with a valid JSON object in this exact format: "
    "{"
    "  \"tos_topic_title\": \"(e.g., Theories)\", "
    "  \"aligned_bloom_level\": \"(e.g., applying)\", "
    "  \"summary\": \"...your concise summary...\", "
    "  \"questions\": ["
    "    {\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": \"A\", "
    "     \"tos_topic_title\": \"(e.g., Theories)\", \"aligned_bloom_level\": \"(e.g., remembering)\"}"
    "  ], "
    "  \"flashcards\": ["
    "    {\"question\": \"What is...?\", \"answer\": \"It is...\", "
    "     \"tos_topic_title\": \"(e.g., Sikolohiyang Filipino)\", \"aligned_bloom_level\": \"(e.g., remembering)\"}"
    "  ]"
    "}"
    "Generate exactly 5 quiz questions and 10 flashcards. "
    "Do not include any markdown formatting, code blocks, or explanatory text."
)

async def _call_gemini_api(system_prompt: str, user_query: str) -> Dict[str, Any]:
    """Helper function to call the Gemini API"""
    if not API_URL:
        raise RuntimeError("Gemini API not configured. Please set GEMINI_API_KEY.")
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload, timeout=60.0)
            response.raise_for_status()
            
            result = response.json()
            text_response = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            if not text_response:
                raise ValueError("AI returned an empty response.")
            
            # Clean the response
            clean_text = text_response.strip()
            clean_text = clean_text.removeprefix("```json").removeprefix("```")
            clean_text = clean_text.removesuffix("```").strip()
            
            return json.loads(clean_text)
            
        except json.JSONDecodeError as e:
            print(f"AI Error: Failed to decode JSON. Raw response: {clean_text[:500]}")
            raise ValueError(f"AI returned invalid JSON: {e}")
        except httpx.HTTPStatusError as e:
            print(f"AI Error: HTTP error {e.response.status_code}: {e.response.text}")
            raise ValueError(f"AI API request failed: {e.response.status_code}")
        except Exception as e:
            print(f"AI Error: Unexpected error: {e}")
            raise ValueError(f"An unexpected error occurred with the AI service: {e}")

def _create_generation_query(pdf_text: str, tos_structure: str) -> str:
    """Combines PDF text and TOS structure into a single query"""
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

Here is the text from the module. Generate your content based ONLY on this text:
---[MODULE TEXT START]---
{pdf_text}
---[MODULE TEXT END]---
"""

async def generate_unified_learning_package(pdf_text: str, tos_structure: str) -> UnifiedLearningPackage:
    """
    Takes PDF text and TOS, returns a single, structured learning
    package containing a summary, quiz, and flashcards.
    """
    user_query = _create_generation_query(pdf_text, tos_structure)
    json_data = await _call_gemini_api(UNIFIED_GENERATION_SYSTEM_PROMPT, user_query)
    
    try:
        return UnifiedLearningPackage.model_validate(json_data)
    except ValidationError as e:
        print(f"AI Validation Error (Unified Package): {e}")
        print(f"Raw AI Response: {json.dumps(json_data, indent=2)[:1000]}")
        raise ValueError(f"AI returned data in the wrong format for a unified package: {e}")