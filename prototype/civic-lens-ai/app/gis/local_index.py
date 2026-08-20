"""
Local Bhubaneswar Geographic Resolution Engine.
Performs sub-millisecond local gazetteer lookups with verified aliases and safe fuzzy matching.
"""
import os
import sqlite3
import difflib
import logging
from typing import List, Optional, Tuple, Dict, Any
from app.schemas import CandidateLocation, LocationClues
from app.gis.normalizer import clean_punctuation, extract_location_phrases

logger = logging.getLogger("civiclens.gis.local_index")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "bhubaneswar_locations.db")


class BhubaneswarLocationIndex:
    """In-memory cached search service over data/bhubaneswar_locations.db"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._cache_loaded = False
        # In-memory dictionary: normalized_alias -> location dict
        self._alias_map: Dict[str, Dict[str, Any]] = {}
        # In-memory list of (normalized_alias, location_dict) for safe fuzzy scan
        self._all_aliases: List[Tuple[str, Dict[str, Any]]] = []
        self._load_cache()

    def _load_cache(self):
        if not os.path.exists(self.db_path):
            logger.warning(f"Bhubaneswar location database not found at {self.db_path}. Local index disabled.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT l.id, l.canonical_name, l.category, l.locality, l.ward, l.latitude, l.longitude, l.source,
                   a.alias_normalized, a.alias_type, a.confidence as alias_conf
            FROM location_aliases a
            JOIN locations l ON a.location_id = l.id
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            for r in rows:
                loc_dict = {
                    "id": r["id"],
                    "canonical_name": r["canonical_name"],
                    "category": r["category"],
                    "locality": r["locality"],
                    "ward": r["ward"],
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "source": r["source"],
                    "alias_type": r["alias_type"],
                    "alias_conf": float(r["alias_conf"])
                }
                alias = r["alias_normalized"]
                self._alias_map[alias] = loc_dict
                self._all_aliases.append((alias, loc_dict))

            conn.close()
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._all_aliases)} location aliases into memory cache from {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to load Bhubaneswar location index cache: {e}")

    def resolve(self, text: str) -> Optional[Tuple[LocationClues, List[CandidateLocation]]]:
        """
        Attempts to resolve the text against the local Bhubaneswar index.
        Returns (LocationClues, [CandidateLocation]) if a confident match is found (conf >= 0.85),
        or None if no confident match is identified (triggering downstream fallback).
        """
        if not self._cache_loaded or not text or not text.strip():
            return None

        candidate_phrases = extract_location_phrases(text)
        if not candidate_phrases:
            return None

        best_match: Optional[Dict[str, Any]] = None
        best_conf = 0.0
        best_matched_alias = ""

        for phrase in candidate_phrases:
            # 1. Exact alias match
            if phrase in self._alias_map:
                loc = self._alias_map[phrase]
                conf = 0.98 if loc.get("source") == "VERIFIED_REGISTRY" else 0.95
                if conf > best_conf:
                    best_match = loc
                    best_conf = conf
                    best_matched_alias = phrase
                    break  # Highest confidence exact match

            # 2. Check if phrase contains known alias (whole word / subphrase match)
            # E.g. "silicon institute, bhubaneswar" contains "silicon institute"
            import re
            for alias, loc in self._all_aliases:
                # City entity (Bhubaneswar) is only matched as exact query, not as subphrase of a detailed sentence
                if loc.get("category") == "city":
                    continue

                if len(alias) >= 4:
                    pattern = r'\b' + re.escape(alias) + r'\b'
                    if re.search(pattern, phrase):
                        # Matched a complete alias subphrase
                        is_verified = (loc.get("source") == "VERIFIED_REGISTRY")
                        if len(alias.split()) > 1:
                            # Multi-word alias match (e.g. "silicon institute", "sum hospital")
                            conf = 0.96 if is_verified else 0.92
                        else:
                            # Single-word landmark/locality alias match (e.g. "silicon", "kiit", "patia")
                            conf = 0.92 if is_verified else 0.88

                        if conf > best_conf:
                            best_conf = conf
                            best_match = loc
                            best_matched_alias = alias

            if best_conf >= 0.95:
                break

        # 3. Safe fuzzy match if no exact or strong substring match found
        if best_conf < 0.85:
            for phrase in candidate_phrases:
                # Do not fuzzy match very short phrases (< 4 chars)
                if len(phrase) < 4:
                    continue

                for alias, loc in self._all_aliases:
                    if len(alias) < 4:
                        continue

                    # Disallow fuzzy matching between wildly different length strings
                    if abs(len(alias) - len(phrase)) > 4:
                        continue

                    ratio = difflib.SequenceMatcher(None, phrase, alias).ratio()
                    # Strict fuzzy similarity threshold >= 0.85
                    if ratio >= 0.85:
                        conf = round(ratio * 0.92, 2)
                        if conf > best_conf:
                            best_conf = conf
                            best_match = loc
                            best_matched_alias = alias

        # Conservative gating: only accept resolution if confidence >= 0.85
        if not best_match or best_conf < 0.85:
            return None

        # Construct full display name adhering to standard format
        locality_str = f", {best_match['locality']}" if best_match.get("locality") else ""
        ward_str = f", {best_match['ward']}" if best_match.get("ward") else ""
        display_name = f"{best_match['canonical_name']}{locality_str}{ward_str}, Bhubaneswar, Odisha, India"

        candidate = CandidateLocation(
            display_name=display_name,
            latitude=best_match["latitude"],
            longitude=best_match["longitude"],
            confidence=round(best_conf, 2),
            is_in_jurisdiction=True,
            source="LocalBhubaneswarIndex"
        )

        clues = LocationClues(
            village_locality=best_match.get("locality"),
            ward=best_match.get("ward"),
            road_street=None,
            landmark=best_match["canonical_name"] if best_match.get("category") != "locality" else None,
            city_district="Bhubaneswar",
            raw_query=f"{best_match['canonical_name']}, Bhubaneswar",
            confidence=round(best_conf, 2)
        )

        return clues, [candidate]

    def reverse_resolve_coordinates(self, lat: float, lon: float, max_distance_km: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Performs a fast spatial reverse lookup from (lat, lon) to the nearest canonical location
        in the Bhubaneswar registry if within max_distance_km (default 0.5 km / 500m).
        Returns the location dict or None if no canonical location is within distance.
        """
        if not self._cache_loaded or lat is None or lon is None:
            return None

        import math
        nearest_loc = None
        min_dist = float("inf")
        seen_ids = set()

        for _, loc in self._all_aliases:
            loc_id = loc.get("id")
            if loc_id in seen_ids:
                continue
            seen_ids.add(loc_id)

            # Skip generic city entity
            if loc.get("category") == "city":
                continue

            loc_lat = loc.get("latitude")
            loc_lon = loc.get("longitude")
            if loc_lat is None or loc_lon is None:
                continue

            # Haversine distance
            R = 6371.0
            dlat = math.radians(loc_lat - lat)
            dlon = math.radians(loc_lon - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(loc_lat)) * math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist = R * c

            if dist < min_dist:
                min_dist = dist
                nearest_loc = loc

        if nearest_loc and min_dist <= max_distance_km:
            return nearest_loc

        return None


# Singleton instance
bhubaneswar_location_index = BhubaneswarLocationIndex()
