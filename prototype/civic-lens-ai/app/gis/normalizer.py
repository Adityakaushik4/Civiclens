"""
Text Normalization and Phrase Extraction Module for Civic Complaints.
Cleans conversational prefixes, handles common transliterations, and isolates location candidate strings.
"""
import re
from typing import List, Optional

# Noise prefixes commonly typed by citizens in civic complaint forms
NOISE_PREFIXES = [
    r'^(?:there is a|there is an|there\'s a|there\'s an)\s+',
    r'^(?:i am reporting a|i am reporting an|i\'m reporting a|i\'m reporting an|reporting a|reporting an)\s+',
    r'^(?:please fix|complaint regarding|issue with|problem of|heavy|severe)\s+',
    r'^(?:pothole|waterlogging|garbage|broken light|streetlight|open drain|drainage issue|road damage|leakage)\s+(?:near|at|in front of|beside|opposite|in|on)\s+',
    r'^(?:near|at|in front of|beside|opposite to|opposite|in|around|behind)\s+',
]

# Standard phonetic replacements for frequent Indian city / locality misspellings
PHONETIC_CANONICAL_MAP = {
    "bhubneshwar": "bhubaneswar",
    "bhubneswar": "bhubaneswar",
    "bhubaneshwar": "bhubaneswar",
    "bbsr": "bhubaneswar",
    "jayadev vihar": "jaydev vihar",
    "jaydeva vihar": "jaydev vihar",
    "sahid nagar": "saheed nagar",
    "nayapali": "nayapalli",
    "patia chhak": "patia square",
    "patia chawk": "patia square",
    "khandagiri chhak": "khandagiri square",
    "rasulgarh chhak": "rasulgarh square",
    "master canteen chhak": "master canteen square",
}


def clean_punctuation(text: str) -> str:
    """Removes punctuation and normalizes whitespace."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'[\(\)\[\]\{\}\.,\/\\\-_:;!?"\']', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def apply_phonetic_normalization(text: str) -> str:
    """Replaces well-known phonetic variations with their canonical forms."""
    t = text.lower()
    for variant, canonical in PHONETIC_CANONICAL_MAP.items():
        # Match whole word or exact phrase
        pattern = r'\b' + re.escape(variant) + r'\b'
        t = re.sub(pattern, canonical, t)
    return t


def extract_location_phrases(text: str) -> List[str]:
    """
    Extracts high-probability candidate location substrings from raw citizen complaint text.
    Returns an ordered list of candidate strings from most specific to general.
    """
    if not text or not text.strip():
        return []

    raw = clean_punctuation(text)
    phrases = []

    # 1. Whole normalized string with phonetics applied
    normalized_full = apply_phonetic_normalization(raw)
    if normalized_full:
        phrases.append(normalized_full)

    # 2. Extract phrase after spatial prepositions (near, at, in front of, beside, opposite, in)
    spatial_pattern = re.compile(
        r'\b(?:near|at|in front of|beside|opposite to|opposite|in|on|behind|around)\b\s+(.*)',
        re.IGNORECASE
    )
    match = spatial_pattern.search(raw)
    if match:
        extracted = match.group(1).strip()
        if len(extracted) >= 3:
            extracted_norm = apply_phonetic_normalization(extracted)
            if extracted_norm not in phrases:
                phrases.append(extracted_norm)

    # 3. Strip leading noise prefixes
    stripped = raw
    for p in NOISE_PREFIXES:
        stripped = re.sub(p, '', stripped, flags=re.IGNORECASE).strip()
    
    if stripped and len(stripped) >= 3:
        stripped_norm = apply_phonetic_normalization(stripped)
        if stripped_norm not in phrases:
            phrases.append(stripped_norm)

    return phrases
