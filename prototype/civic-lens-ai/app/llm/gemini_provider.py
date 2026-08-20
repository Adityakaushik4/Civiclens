import json
import logging
import asyncio
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import settings
from app.llm.base import LLMProvider, LLMProviderError
from app.taxonomy import get_taxonomy_prompt_string, CATEGORIES_LIST

logger = logging.getLogger("civiclens.gemini")


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.LLM_MODEL
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY environment variable is not configured.")
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise LLMProviderError(f"Gemini client initialization failed: {str(e)}")

    async def extract_structured(
        self, text: str, language: str, retry_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        taxonomy_info = get_taxonomy_prompt_string()
        categories_str = ", ".join(sorted(list(CATEGORIES_LIST)))

        system_instruction = (
            "You are the CivicLens AI Engine. Your task is to analyze civic complaints "
            "submitted by citizens in any language (English, Hindi, Odia, etc.) and extract structured JSON information.\n\n"
            f"Mandatory Category Taxonomy (Must be ONE of these exact strings):\n{categories_str}\n\n"
            f"Configured Subcategories per Category:\n{taxonomy_info}\n\n"
            "Requirements:\n"
            "1. 'category': Must be ONE of the exact categories listed above. Never invent new categories.\n"
            "2. 'subcategory': Pick the most appropriate subcategory from the taxonomy, or 'OTHER'.\n"
            "3. 'severity': An integer from 0 (very minor) to 5 (critical emergency/hazard).\n"
            "4. 'safety_risk': Boolean (true if this issue poses an immediate safety risk/hazard to human life or health, false otherwise).\n"
            "5. 'public_impact': An integer from 0 (affects single person) to 5 (widespread community/citywide impact).\n"
            "6. 'location_description': Exact location description mentioned in the complaint (e.g. 'near the school'), or empty string if not specified.\n"
            "7. 'summary': A clear, concise English summary of the issue (1 sentence).\n"
            "8. 'confidence': A float between 0.0 and 1.0 representing how confident you are in the accuracy of this extraction (based on language clarity, specificity of issue, and taxonomy match).\n\n"
            "You MUST output valid JSON matching this exact structure:\n"
            "{\n"
            '  "category": "ROAD_DAMAGE",\n'
            '  "subcategory": "POTHOLE",\n'
            '  "severity": 4,\n'
            '  "safety_risk": true,\n'
            '  "public_impact": 4,\n'
            '  "location_description": "near the school",\n'
            '  "summary": "Large pothole near school creating safety risk",\n'
            '  "confidence": 0.92\n'
            "}"
        )

        user_content = f"Complaint Text ({language}): {text}"
        if retry_prompt:
            user_content += f"\n\n[CORRECTION NOTICE - PREVIOUS OUTPUT WAS INVALID]:\n{retry_prompt}\nPlease fix the schema errors and return strictly valid JSON."

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            if not response or not response.text:
                raise LLMProviderError("Empty response received from Gemini API.")

            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            data = json.loads(cleaned_text)
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Gemini response: {e}")
            raise LLMProviderError(f"Malformed JSON returned by Gemini API: {str(e)}")
        except APIError as e:
            logger.error(f"Gemini API Error: {e}")
            raise LLMProviderError(f"Gemini API call failed: {str(e)}")
        except Exception as e:
            if isinstance(e, LLMProviderError):
                raise e
            logger.error(f"Unexpected error during Gemini API execution: {e}")
            raise LLMProviderError(f"LLM Provider Error: {str(e)}")

    async def extract_location_clues(self, text: str) -> Dict[str, Any]:
        system_instruction = (
            "You are the CivicLens AI Engine. Your task is to extract location clues "
            "from civic complaint text (in English, Hindi, Odia, or any language) to form a search query for geocoding.\n\n"
            "Requirements:\n"
            "1. 'village_locality': Village, locality, or neighborhood name if present, else null.\n"
            "2. 'ward': Ward number or name if present, else null.\n"
            "3. 'road_street': Road or street name if present, else null.\n"
            "4. 'landmark': Prominent landmark (school, hospital, bus stop, market, college, etc.), else null.\n"
            "5. 'city_district': City or district if mentioned, else null.\n"
            "6. 'raw_query': A synthesized, concise search query string combining the most confident clues for a geocoder like Nominatim. Translate any non-English place names or landmarks into Latin script if needed. Do NOT include phrases like 'near' or 'in front of'. E.g., 'ITER Bhubaneswar' or 'Jaydev Vihar Bhubaneswar'. If no specific physical location (landmark, street, locality, city) is identified in the text, set raw_query to an empty string ''.\n"
            "7. 'confidence': A float between 0.0 and 1.0 representing how confident you are that a specific physical location was mentioned. If no specific physical location is identified, set confidence to 0.0.\n\n"
            "You MUST output valid JSON matching this exact structure:\n"
            "{\n"
            '  "village_locality": "Khandia",\n'
            '  "ward": null,\n'
            '  "road_street": "Main Road",\n'
            '  "landmark": "Bus Stop",\n'
            '  "city_district": "Bhubaneswar",\n'
            '  "raw_query": "Khandia Bus Stop, Main Road, Bhubaneswar",\n'
            '  "confidence": 0.85\n'
            "}"
        )

        user_content = f"Complaint Text: {text}"

        try:
            task = asyncio.create_task(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
            )
            done, pending = await asyncio.wait([task], timeout=15.0)
            
            if pending:
                raise TimeoutError("Gemini API timed out.")
                
            response = task.result()
            if not response or not response.text:
                raise LLMProviderError("Empty response received from Gemini API for location extraction.")

            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            data = json.loads(cleaned_text)
            return data
        except TimeoutError:
            logger.error("Gemini API timed out during location extraction.")
            raise LLMProviderError("LLM service timed out due to high demand. Please try again.")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Gemini response (location): {e}")
            raise LLMProviderError(f"Malformed JSON returned by Gemini API for location: {str(e)}")
        except APIError as e:
            logger.error(f"Gemini API Error (location): {e}")
            raise LLMProviderError(f"Gemini API call failed for location: {str(e)}")
        except Exception as e:
            if isinstance(e, LLMProviderError):
                raise e
            logger.error(f"Unexpected error during Gemini API execution (location): {e}")
            raise LLMProviderError(f"LLM Provider Error (location): {str(e)}")
