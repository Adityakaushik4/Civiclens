"""
Deterministic Civic Intent Classification Rules & Safeguards.
Enforces high-confidence primary category detection from citizen text.
"""
import re
from typing import Optional, Tuple
from app.taxonomy import Category

# High-confidence intent rules mapping regex patterns to (Category, Subcategory, Severity)
DETERMINISTIC_INTENT_RULES = [
    # 1. STREETLIGHT (High precedence to prevent false drainage/garbage matching)
    (
        r'\b(?:streetlight|streetlights|street light|street lights|street lamp|street lamps|lamp post|lamp posts|light pole|light poles|broken light|no light|light not working|lights not working|street lights off|lights are off)\b',
        Category.STREETLIGHT,
        "LIGHT_OUT",
        2
    ),
    # 2. ROAD_DAMAGE
    (
        r'\b(?:pothole|potholes|broken road|road damage|road damaged|damaged road|cracked road|unpaved road|pit on road|gadttha)\b',
        Category.ROAD_DAMAGE,
        "POTHOLE",
        4
    ),
    # 3. GARBAGE
    (
        r'\b(?:garbage|trash|waste dumped|dumped waste|uncollected garbage|overflowing bin|dustbin overflow|garbage pile|litter)\b',
        Category.GARBAGE,
        "UNCOLLECTED_GARBAGE",
        3
    ),
    # 4. DRAINAGE
    (
        r'\b(?:waterlogging|water logged|waterlog|flooded road|drain overflow|blocked drain|open drain|drainage overflow|drainage blocked|drainage issue|drainage problem)\b',
        Category.DRAINAGE,
        "WATERLOGGING",
        4
    ),
    # 5. SEWERAGE
    (
        r'\b(?:sewage|sewer|sewer overflow|blocked sewer|open manhole|sewage leak|gully overflow)\b',
        Category.SEWERAGE,
        "SEWAGE_LEAK",
        4
    ),
    # 6. WATER_SUPPLY
    (
        r'\b(?:water supply|no water|pipe leakage|leaking pipe|water pipe burst|contaminated water|water line)\b',
        Category.WATER_SUPPLY,
        "PIPE_LEAKAGE",
        3
    ),
    # 7. ELECTRICITY
    (
        r'\b(?:power outage|damaged transformer|hanging wires|wire sparking|electric transformer)\b',
        Category.ELECTRICITY,
        "POWER_OUTAGE",
        4
    ),
]


def detect_deterministic_category(text: str) -> Optional[Tuple[Category, str, int]]:
    """
    Scans text for explicit, unambiguous civic intent patterns.
    Returns (Category, subcategory_string, severity_int) if a strong match is identified,
    otherwise None.
    """
    if not text or not text.strip():
        return None

    t_lower = text.lower()
    for pattern, category, default_subcat, default_sev in DETERMINISTIC_INTENT_RULES:
        if re.search(pattern, t_lower):
            # Refine subcategory based on text details
            subcat = default_subcat
            if category == Category.STREETLIGHT:
                if "pole" in t_lower:
                    subcat = "DAMAGED_POLE"
                elif "wire" in t_lower:
                    subcat = "EXPOSED_WIRING"
                elif "flicker" in t_lower:
                    subcat = "FLICKERING_LIGHT"
            elif category == Category.DRAINAGE:
                if "blocked" in t_lower:
                    subcat = "BLOCKED_DRAIN"
                elif "open" in t_lower:
                    subcat = "OPEN_DRAIN"
            return category, subcat, default_sev

    return None
