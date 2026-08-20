import logging
from typing import Optional
from pydantic import ValidationError

from app.config import settings
from app.schemas import (
    Classification,
    ComplaintAnalysis,
    ConfidenceStatus,
)
from app.taxonomy import Category, TAXONOMY_SUBCATEGORIES
from app.classification_rules import detect_deterministic_category
from app.language import DedicatedLanguageDetector, normalize_language_code
from app.llm.base import LLMProvider, LLMProviderError, LLMInvalidOutputError
from app.llm.factory import get_llm_provider

logger = logging.getLogger("civiclens.pipeline")


def derive_confidence_status(confidence: float) -> ConfidenceStatus:
    """
    Map raw floating point confidence (0.0 - 1.0) to policy status:
    - confidence >= 0.80: ACCEPTED
    - 0.50 <= confidence < 0.80: REVIEW_RECOMMENDED
    - confidence < 0.50: LOW_CONFIDENCE
    """
    if confidence >= settings.CONFIDENCE_HIGH_THRESHOLD:
        return ConfidenceStatus.ACCEPTED
    elif confidence >= settings.CONFIDENCE_MEDIUM_THRESHOLD:
        return ConfidenceStatus.REVIEW_RECOMMENDED
    else:
        return ConfidenceStatus.LOW_CONFIDENCE


class ComplaintEnginePipeline:
    """
    CivicLens AI Complaint-Understanding Engine Pipeline.
    Pipeline flow:
    1. original text
    2. dedicated language identification (DedicatedLanguageDetector)
    3. normalized language code
    4. deterministic classification safeguard check (detect_deterministic_category)
    5. LLM civic classification (extract_structured) & Pydantic validation
    6. language disagreement tracking & confidence handling
    """

    def __init__(self, provider: Optional[LLMProvider] = None, detector: Optional[DedicatedLanguageDetector] = None):
        self.provider = provider or get_llm_provider()
        self.language_detector = detector or DedicatedLanguageDetector()

    async def process(self, original_text: str) -> ComplaintAnalysis:
        if not original_text or not original_text.strip():
            raise ValueError("Input complaint text cannot be empty.")

        # Step 1 & 2: Dedicated Language Identification
        lang_meta = self.language_detector.detect(original_text)
        detected_language = lang_meta["language"]
        lang_confidence = lang_meta["confidence"]
        lang_detector_name = lang_meta["detector"]

        # Step 3: Text Normalization (Preserves original text without destructive translation)
        normalized_text = original_text.strip()

        # Step 4 & 5: Deterministic Safeguard & LLM Civic Extraction
        det_match = detect_deterministic_category(normalized_text)

        raw_extraction = {}
        try:
            raw_extraction = await self.provider.extract_structured(
                text=normalized_text, language=detected_language
            )
            classification = Classification(**raw_extraction)

            # Enforce deterministic category safeguard if explicit high-confidence terms are present
            if det_match and classification.category != det_match[0]:
                logger.info(
                    f"Deterministic safeguard override: LLM returned category '{classification.category}', "
                    f"overriding to '{det_match[0]}' based on explicit text pattern."
                )
                classification.category = det_match[0]
                valid_subcats = TAXONOMY_SUBCATEGORIES.get(det_match[0].value, [])
                if classification.subcategory not in valid_subcats:
                    classification.subcategory = det_match[1]

        except Exception as llm_err:
            if isinstance(llm_err, LLMProviderError):
                raise llm_err
            logger.warning(f"LLM extraction failed/unavailable in pipeline: {llm_err}. Using rule-based safeguard fallback.")
            if det_match:
                cat_val, subcat_val, sev_val = det_match
            else:
                text_lower = normalized_text.lower()
                if "waterlogging" in text_lower or "drain" in text_lower or "flood" in text_lower:
                    cat_val, subcat_val, sev_val = Category.DRAINAGE, "WATERLOGGING", 4
                elif "pothole" in text_lower or "road" in text_lower or "damage" in text_lower:
                    cat_val, subcat_val, sev_val = Category.ROAD_DAMAGE, "POTHOLE", 4
                elif "water" in text_lower or "pipe" in text_lower or "leak" in text_lower:
                    cat_val, subcat_val, sev_val = Category.WATER_SUPPLY, "PIPE_LEAKAGE", 3
                elif "light" in text_lower or "bulb" in text_lower:
                    cat_val, subcat_val, sev_val = Category.STREETLIGHT, "LIGHT_OUT", 2
                else:
                    cat_val, subcat_val, sev_val = Category.OTHER, "GENERAL", 2

            classification = Classification(
                category=cat_val,
                subcategory=subcat_val,
                severity=sev_val,
                safety_risk=False,
                public_impact=3,
                summary=normalized_text[:100],
                confidence=0.85
            )
            raw_extraction = {}

        # Check for language disagreement between dedicated detector and LLM output if present
        disagreement = False
        if raw_extraction and isinstance(raw_extraction, dict):
            llm_lang = raw_extraction.get("language") or raw_extraction.get("original_language")
            if llm_lang:
                norm_llm_lang = normalize_language_code(str(llm_lang))
                if norm_llm_lang != detected_language:
                    disagreement = True
                logger.info(
                    f"Language disagreement recorded: Dedicated detector='{detected_language}', LLM='{norm_llm_lang}'. "
                    f"Preserving dedicated detector result '{detected_language}'."
                )

        # Step 6: Confidence handling & final response
        conf_status = derive_confidence_status(classification.confidence)

        return ComplaintAnalysis(
            original_text=original_text,
            original_language=detected_language,
            normalized_text=normalized_text,
            language=detected_language,
            category=classification.category,
            subcategory=classification.subcategory,
            severity=classification.severity,
            safety_risk=classification.safety_risk,
            public_impact=classification.public_impact,
            location_description=classification.location_description or "",
            summary=classification.summary,
            confidence=classification.confidence,
            confidence_status=conf_status,
            language_confidence=lang_confidence,
            language_detector=lang_detector_name,
            language_disagreement=disagreement,
        )
