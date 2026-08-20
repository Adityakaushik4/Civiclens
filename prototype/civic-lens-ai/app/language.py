import re
import logging
from typing import Dict, Any
from langdetect import detect_langs, DetectorFactory

DetectorFactory.seed = 0
logger = logging.getLogger("civiclens.language")

# Unicode script ranges for Indic and other writing systems
SCRIPT_RANGES = [
    ("or", re.compile(r"[\u0B00-\u0B7F]")),  # Odia script
    ("hi", re.compile(r"[\u0900-\u097F]")),  # Devanagari (Hindi, Marathi, Nepali)
    ("bn", re.compile(r"[\u0980-\u09FF]")),  # Bengali
    ("pa", re.compile(r"[\u0A00-\u0A7F]")),  # Gurmukhi (Punjabi)
    ("gu", re.compile(r"[\u0A80-\u0AFF]")),  # Gujarati
    ("ta", re.compile(r"[\u0B80-\u0BFF]")),  # Tamil
    ("te", re.compile(r"[\u0C00-\u0C7F]")),  # Telugu
    ("kn", re.compile(r"[\u0C80-\u0CFF]")),  # Kannada
    ("ml", re.compile(r"[\u0D00-\u0D7F]")),  # Malayalam
]

LATIN_RE = re.compile(r"[a-zA-Z]")


def normalize_language_code(code: str) -> str:
    """Normalize language code variants to standard 2-letter ISO codes."""
    if not code:
        return "en"
    code = code.lower().strip()
    mapping = {
        "or": "or",
        "ori": "or",
        "odia": "or",
        "hi": "hi",
        "hin": "hi",
        "hindi": "hi",
        "en": "en",
        "eng": "en",
        "english": "en",
    }
    return mapping.get(code, code[:2])


class DedicatedLanguageDetector:
    """
    Dedicated language identification layer.
    Combines Unicode script range analysis (100% deterministic for distinct scripts like Odia)
    with statistical language detection (langdetect) for Latin & mixed scripts.
    """

    def detect(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "language": "en",
                "confidence": 0.0,
                "detector": "fallback_empty"
            }

        cleaned_text = text.strip()
        non_space_chars = len(re.sub(r"\s+", "", cleaned_text)) or 1

        # Step 1: Unicode Script Character Analysis (Indic / Non-Latin scripts)
        script_counts = {}
        for lang_code, pattern in SCRIPT_RANGES:
            matches = len(pattern.findall(cleaned_text))
            if matches > 0:
                script_counts[lang_code] = matches

        if script_counts:
            dominant_lang, char_count = max(script_counts.items(), key=lambda item: item[1])
            ratio = char_count / non_space_chars
            # High confidence if script characters form significant portion of text
            confidence = min(1.0, max(0.85, ratio * 1.5))
            logger.debug(f"Script detection: {dominant_lang} ({char_count}/{non_space_chars} chars, conf={confidence:.2f})")
            return {
                "language": dominant_lang,
                "confidence": round(confidence, 2),
                "detector": "unicode_script_heuristic"
            }

        # Step 2: Statistical Detection for Latin / Romanized text
        latin_matches = len(LATIN_RE.findall(cleaned_text))
        if latin_matches > 0:
            # If short single word in pure ASCII/Latin, default to 'en' unless clear statistical match
            if len(cleaned_text.split()) <= 2 and all(ord(c) < 128 for c in cleaned_text):
                return {
                    "language": "en",
                    "confidence": 0.85,
                    "detector": "latin_script_heuristic"
                }

            # English civic context override: Indian proper nouns often confuse statistical langdetect 
            # into predicting Indonesian (id) or Swahili (sw).
            english_signals = {
                "waterlogging", "garbage", "pothole", "streetlight", "road", "drain",
                "leak", "sewer", "trash", "near", "the", "is", "broken", "issue", "problem",
                "water", "street", "light", "dump", "please", "fix", "repair", "not", "working"
            }
            words = set(re.findall(r'[a-z]+', cleaned_text.lower()))
            if english_signals & words:
                return {
                    "language": "en",
                    "confidence": 0.90,
                    "detector": "english_civic_heuristic"
                }

            try:
                detected_langs = detect_langs(cleaned_text)
                if detected_langs:
                    top_match = detected_langs[0]
                    norm_code = normalize_language_code(top_match.lang)
                    prob = float(top_match.prob)
                    return {
                        "language": norm_code,
                        "confidence": round(prob, 2),
                        "detector": "statistical_langdetect"
                    }
            except Exception as e:
                logger.debug(f"Statistical langdetect error: {e}")

            return {
                "language": "en",
                "confidence": 0.75,
                "detector": "latin_script_fallback"
            }

        # Step 3: Low confidence fallback
        return {
            "language": "en",
            "confidence": 0.30,
            "detector": "fallback_uncertain"
        }
