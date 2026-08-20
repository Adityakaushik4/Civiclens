from enum import Enum
from typing import Dict, List, Set


class Category(str, Enum):
    ROAD_DAMAGE = "ROAD_DAMAGE"
    GARBAGE = "GARBAGE"
    STREETLIGHT = "STREETLIGHT"
    DRAINAGE = "DRAINAGE"
    WATER_SUPPLY = "WATER_SUPPLY"
    SEWERAGE = "SEWERAGE"
    ELECTRICITY = "ELECTRICITY"
    PUBLIC_TOILET = "PUBLIC_TOILET"
    PARK = "PARK"
    TRAFFIC = "TRAFFIC"
    OTHER = "OTHER"


class Department(str, Enum):
    ROADS_PWD = "Roads & PWD"
    SANITATION_WASTE = "Sanitation & Waste Management"
    WATER_SUPPLY = "Water Supply"
    ELECTRICAL_LIGHTING = "Electrical / Street Lighting"
    DRAINAGE_SEWERAGE = "Drainage & Sewerage"
    PUBLIC_HEALTH = "Public Health"
    TRAFFIC_SAFETY = "Traffic & Road Safety"
    PARKS_HORTICULTURE = "Parks & Horticulture"
    STREET_CLEANING = "Street Cleaning"
    PUBLIC_TOILETS = "Public Toilets"
    ENCROACHMENT = "Encroachment / Illegal Construction"
    BUILDING_INFRASTRUCTURE = "Building & Infrastructure"
    ENVIRONMENT_POLLUTION = "Environment / Pollution"
    ANIMAL_CONTROL = "Animal Control"
    FIRE_EMERGENCY = "Fire & Emergency Services"
    MUNICIPAL_ADMIN = "Municipal Administration"
    OTHER_GENERAL = "Other / General"


CATEGORIES_LIST: Set[str] = {c.value for c in Category}

TAXONOMY_SUBCATEGORIES: Dict[str, List[str]] = {
    Category.ROAD_DAMAGE.value: [
        "POTHOLE", "CRACKED_ROAD", "UNPAVED_ROAD", "OTHER"
    ],
    Category.GARBAGE.value: [
        "UNCOLLECTED_GARBAGE", "OVERFLOWING_BIN", "ILLEGAL_DUMPING", "DEAD_ANIMAL", "OTHER"
    ],
    Category.STREETLIGHT.value: [
        "LIGHT_OUT", "FLICKERING_LIGHT", "DAMAGED_POLE", "EXPOSED_WIRING", "OTHER"
    ],
    Category.DRAINAGE.value: [
        "BLOCKED_DRAIN", "OPEN_DRAIN", "BROKEN_DRAIN_COVER", "WATER_OVERFLOW", "WATERLOGGING", "OTHER"
    ],
    Category.WATER_SUPPLY.value: [
        "NO_WATER", "LOW_PRESSURE", "CONTAMINATED_WATER", "PIPE_LEAKAGE", "OTHER"
    ],
    Category.SEWERAGE.value: [
        "SEWAGE_LEAK", "BLOCKED_SEWER", "OPEN_MANHOLE", "ODOR", "OTHER"
    ],
    Category.ELECTRICITY.value: [
        "POWER_OUTAGE", "DAMAGED_TRANSFORMER", "HANGING_WIRES", "SPARKING", "OTHER"
    ],
    Category.PUBLIC_TOILET.value: [
        "DIRTY_TOILET", "NO_WATER_TOILET", "BROKEN_FIXTURES", "CLOSED_TOILET", "OTHER"
    ],
    Category.PARK.value: [
        "BROKEN_EQUIPMENT", "UNMAINTAINED_GRASS", "LITTER_IN_PARK", "VANDALISM", "OTHER"
    ],
    Category.TRAFFIC.value: [
        "TRAFFIC_CONGESTION", "NON_FUNCTIONAL_SIGNAL", "ILLEGAL_PARKING", "MISSING_SIGNAGE", "OTHER"
    ],
    Category.OTHER.value: [
        "GENERAL_CIVIC_ISSUE", "OTHER"
    ]
}


def get_taxonomy_prompt_string() -> str:
    """Format taxonomy for system prompt guidance."""
    lines = []
    for cat, subcats in TAXONOMY_SUBCATEGORIES.items():
        lines.append(f"- {cat}: {', '.join(subcats)}")
    return "\n".join(lines)
