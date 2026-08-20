import json
import logging
import asyncio
from typing import Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import settings
from app.schemas import (
    VisualAnalysis,
    ComplaintAnalysis,
    ConfidenceStatus,
    Category,
)
from app.taxonomy import get_taxonomy_prompt_string, CATEGORIES_LIST
from app.language import DedicatedLanguageDetector
from app.pipeline import derive_confidence_status, ComplaintEnginePipeline
from app.vision.base import VisionProvider, VisionProviderError, VisionInvalidImageError

logger = logging.getLogger("civiclens.vision.gemini")


def _consume_task_exception(t: asyncio.Task) -> None:
    """Consume exception from background task to prevent 'Task exception was never retrieved' log on timeout."""
    try:
        if not t.cancelled():
            t.exception()
    except (asyncio.CancelledError, Exception):
        pass


class GeminiVisionProvider(VisionProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.get_vision_api_key()
        self.model = model or settings.get_vision_model()
        if not self.api_key:
            raise VisionProviderError("Vision API key is not configured.")
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Vision client: {e}")
            raise VisionProviderError(f"Gemini Vision client initialization failed: {str(e)}")

    async def analyze_image(
        self, file_path: str, mime_type: str, optional_text: Optional[str] = None
    ) -> Tuple[VisualAnalysis, ComplaintAnalysis, bool, Optional[str]]:
        uploaded_file = None
        try:
            # Step 1: Upload image file to Gemini Files API
            uploaded_file = self.client.files.upload(
                file=file_path,
                config=types.UploadFileConfig(mime_type=mime_type)
            )

            taxonomy_info = get_taxonomy_prompt_string()
            categories_str = ", ".join(sorted(list(CATEGORIES_LIST)))

            system_instruction = (
                "You are the CivicLens Multimodal Vision AI Engine. Your task is to analyze civic issue photographs "
                "submitted by citizens, optional accompanying complaint text, and extract structured JSON information.\n\n"
                f"Mandatory Category Taxonomy (Must be ONE of these exact strings):\n{categories_str}\n\n"
                f"Configured Subcategories per Category:\n{taxonomy_info}\n\n"
                "Rules:\n"
                "1. Inspect the image for visible municipal/civic issues (potholes, garbage, uncollected trash, streetlight damage, drainage/waterlogging, sewage, transformer/wire hazards, damaged park equipment, traffic issues, etc.).\n"
                "2. If NO civic issue is visible (e.g. household object, pet, indoor selfie, normal car, blurry/unusable image): set 'visible_issue': false, 'category': 'OTHER', 'subcategory': 'GENERAL_CIVIC_ISSUE', 'severity': 0, 'public_impact': 0, 'confidence': 0.2.\n"
                "3. Assess what is visually depicted in the image as 'visual_analysis'.\n"
                "4. SEVERITY RULES:\n"
                "   - Do NOT automatically replace or increase primary complaint severity using visual severity when text and visual evidence describe DIFFERENT categories.\n"
                "   - When citizen text and visual evidence describe DIFFERENT categories: Citizen category = PRIMARY, Citizen severity = PRIMARY, Visual severity = SUPPORTING EVIDENCE ONLY for visual_analysis.\n"
                "   - When text and image describe the SAME category/issue: Use both sources as evidence for severity. Visual severity is allowed to support or refine the result only when it is relevant to the primary complaint.\n"
                "   - Do not invent severity facts that are not supported by either the citizen's report or the visible evidence.\n\n"
                "Output strictly valid JSON matching this exact structure:\n"
                "{\n"
                '  "visual_analysis": {\n'
                '    "visible_issue": true,\n'
                '    "category": "ROAD_DAMAGE",\n'
                '    "subcategory": "POTHOLE",\n'
                '    "severity": 4,\n'
                '    "safety_risk": true,\n'
                '    "public_impact": 4,\n'
                '    "description": "Large pothole occupying main roadway",\n'
                '    "confidence": 0.91\n'
                '  }\n'
                "}"
            )

            user_prompt = "Analyze this civic issue photograph."
            if optional_text and optional_text.strip():
                user_prompt += f"\nAccompanying User Text Complaint: {optional_text.strip()}"
            task = asyncio.create_task(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=[uploaded_file, user_prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
            )
            task.add_done_callback(_consume_task_exception)
            done, pending = await asyncio.wait([task], timeout=45.0)
            
            if pending:
                task.cancel()
                raise TimeoutError("Gemini Vision API timed out.")
                
            response = task.result()

            if not response or not response.text:
                raise VisionProviderError("Empty response received from Gemini Vision API.")

            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            data = json.loads(cleaned_text)

            # Extract visual_analysis block
            v_block = data.get("visual_analysis", {})
            v_issue = bool(v_block.get("visible_issue", True))
            v_cat_str = str(v_block.get("category", "OTHER")).upper().strip()
            if v_cat_str not in CATEGORIES_LIST:
                v_cat_str = "OTHER"
            
            v_sub = str(v_block.get("subcategory", "OTHER")).upper().strip()
            v_sev = min(5, max(0, int(v_block.get("severity", 0))))
            v_risk = bool(v_block.get("safety_risk", False))
            v_imp = min(5, max(0, int(v_block.get("public_impact", 0))))
            v_desc = str(v_block.get("description", "Image analyzed"))
            v_conf = min(1.0, max(0.0, float(v_block.get("confidence", 0.5))))

            visual_analysis = VisualAnalysis(
                visible_issue=v_issue,
                category=Category(v_cat_str),
                subcategory=v_sub,
                severity=v_sev,
                safety_risk=v_risk,
                public_impact=v_imp,
                description=v_desc,
                confidence=v_conf
            )

            # Deterministic Evidence Fusion based on Citizen Intent Precedence Rule & Severity Rules
            has_text = bool(optional_text and optional_text.strip())

            if has_text:
                clean_text = optional_text.strip()
                pipeline = ComplaintEnginePipeline()
                text_analysis = await pipeline.process(clean_text)

                if text_analysis.category == visual_analysis.category:
                    disagreement = False
                    disagreement_reason = None
                    # SAME category: visual severity supports/refines primary severity
                    if visual_analysis.visible_issue:
                        refined_severity = max(text_analysis.severity, visual_analysis.severity)
                    else:
                        refined_severity = text_analysis.severity
                    complaint_analysis = text_analysis.model_copy(update={"severity": refined_severity})
                else:
                    disagreement = True
                    text_cat_label = text_analysis.category.value.lower().replace("_", " ")
                    vis_cat_label = visual_analysis.category.value.lower().replace("_", " ")
                    disagreement_reason = (
                        f"Citizen reported a {text_cat_label} issue, while the uploaded image "
                        f"visibly shows {vis_cat_label} and does not clearly verify the {text_cat_label}."
                    )
                    # DIFFERENT categories: Citizen category = PRIMARY, Citizen severity = PRIMARY
                    # Visual severity = SUPPORTING EVIDENCE ONLY on visual_analysis
                    # Do NOT increase or replace primary complaint severity with visual severity
                    complaint_analysis = text_analysis
            else:
                disagreement = False
                disagreement_reason = None

                det_result = DedicatedLanguageDetector().detect(v_desc)
                orig_lang = det_result["language"]
                lang_conf = det_result["confidence"]
                lang_det_name = det_result["detector"]
                conf_status = derive_confidence_status(v_conf)

                complaint_analysis = ComplaintAnalysis(
                    original_text=v_desc,
                    original_language=orig_lang,
                    normalized_text=v_desc,
                    language=orig_lang,
                    category=visual_analysis.category,
                    subcategory=visual_analysis.subcategory,
                    severity=visual_analysis.severity,
                    safety_risk=visual_analysis.safety_risk,
                    public_impact=visual_analysis.public_impact,
                    location_description="",
                    detailed_description=v_desc,
                    summary=v_desc,
                    confidence=v_conf,
                    confidence_status=conf_status,
                    language_confidence=lang_conf,
                    language_detector=lang_det_name,
                    language_disagreement=False,
                )

            return visual_analysis, complaint_analysis, disagreement, disagreement_reason
        except TimeoutError:
            logger.error("Gemini Vision API timed out.")
            raise VisionProviderError("Vision service timed out due to high demand. Please try again.")
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON from Gemini Vision: {e}")
            raise VisionProviderError(f"Malformed JSON from Vision service: {str(e)}")
        except APIError as e:
            logger.error(f"Gemini Vision API Error: {e}")
            raise VisionProviderError(f"Gemini Vision service failed: {str(e)}")
        except Exception as e:
            if isinstance(e, (VisionProviderError, VisionInvalidImageError)):
                raise e
            logger.error(f"Unexpected error during Vision analysis: {e}")
            raise VisionProviderError(f"Vision Error: {str(e)}")
        finally:
            if uploaded_file and hasattr(uploaded_file, "name"):
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception as del_err:
                    logger.debug(f"Failed to delete uploaded remote image file: {del_err}")
