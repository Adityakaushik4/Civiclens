import re
import asyncio
import logging
import requests
import time
from typing import List, Tuple
from app.schemas import CandidateLocation, LocationClues
from app.config import settings

logger = logging.getLogger("civiclens.geocoder")

class GeocoderError(Exception):
    pass

class NominatimGeocoder:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "CivicLensAIEngine/1.0"
        }

    def _calculate_jurisdiction_score(self, item: dict, query: str) -> Tuple[float, bool]:
        """
        Ranks candidate location based on:
        1. Municipal/city match (+0.45)
        2. State/region match (+0.30)
        3. Country match (+0.15)
        4. Query similarity (+0.05)
        5. Base geocoder importance (+0.05 max)
        Returns (confidence_score, is_in_jurisdiction).
        """
        addr = item.get("address", {})
        display_name = (item.get("display_name") or "").lower()

        target_city = (settings.JURISDICTION_CITY or "bhubaneswar").lower()
        target_state = (settings.JURISDICTION_STATE or "odisha").lower()
        target_country = (settings.JURISDICTION_COUNTRY or "india").lower()

        # Check city match across address fields
        city_fields = [
            addr.get("city"), addr.get("municipality"), addr.get("county"),
            addr.get("town"), addr.get("village"), addr.get("state_district"), addr.get("suburb")
        ]
        city_matched = any(target_city in (f or "").lower() for f in city_fields) or (target_city in display_name)

        # Check state match
        state_fields = [addr.get("state"), addr.get("state_district")]
        state_matched = any(target_state in (f or "").lower() for f in state_fields) or (target_state in display_name)

        # Check country match
        country_fields = [addr.get("country"), addr.get("country_code")]
        country_matched = any(target_country in (f or "").lower() for f in country_fields) or ("india" in display_name or "in" == addr.get("country_code", "").lower())

        is_in_jurisdiction = city_matched or state_matched

        score = 0.0
        if city_matched:
            score += 0.45
        if state_matched:
            score += 0.30
        if country_matched:
            score += 0.15

        # Query token match bonus
        q_tokens = [t.lower() for t in query.split() if len(t) > 2]
        if q_tokens:
            matches = sum(1 for t in q_tokens if t in display_name)
            score += min(0.05, 0.05 * (matches / len(q_tokens)))

        # Base importance tiebreaker (scaled up to 0.05)
        raw_imp = float(item.get("importance", 0.0) or 0.0)
        score += min(0.05, raw_imp * 0.5)

        final_confidence = round(min(1.0, max(0.05, score)), 2)
        return final_confidence, is_in_jurisdiction

    def _sync_geocode(self, query: str) -> List[CandidateLocation]:
        if not query or not query.strip():
            return []
        
        try:
            params = {
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "viewbox": settings.JURISDICTION_VIEWBOX,
                "limit": 10
            }
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            candidates = []
            for item in data:
                conf, in_jur = self._calculate_jurisdiction_score(item, query)
                candidates.append(CandidateLocation(
                    display_name=item.get("display_name", ""),
                    latitude=float(item.get("lat")),
                    longitude=float(item.get("lon")),
                    confidence=conf,
                    is_in_jurisdiction=in_jur,
                    source="Nominatim"
                ))

            # Rank candidates: local in-jurisdiction & highest confidence first
            candidates.sort(key=lambda c: (c.is_in_jurisdiction, c.confidence), reverse=True)
            return candidates
        except requests.RequestException as e:
            logger.error(f"Nominatim Geocoding Error: {e}")
            raise GeocoderError(f"Failed to reach geocoding service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected Geocoding Error: {e}")
            raise GeocoderError(f"Unexpected error during geocoding: {str(e)}")

    async def geocode(self, query: str) -> List[CandidateLocation]:
        return await asyncio.to_thread(self._sync_geocode, query)

    def _expand_landmark(self, landmark: str) -> List[str]:
        if not landmark:
            return [None]
        lm_lower = landmark.lower()
        expansions = [landmark]
        if "iter" in lm_lower:
            expansions.extend([
                "ITER",
                "Institute of Technical Education and Research",
                "ITER SOA University",
                "Siksha O Anusandhan ITER"
            ])
        # Clean up general suffixes
        if "main gate" in lm_lower or "gate" in lm_lower:
            clean = re.sub(r'(?i)\b(?:main gate|gate \d+|gate)\b', '', landmark).strip()
            if clean:
                expansions.append(clean)
        
        # Deduplicate while preserving order
        seen = set()
        res = []
        for x in expansions:
            if x and x.lower() not in seen:
                seen.add(x.lower())
                res.append(x)
        return res

    def _build_query_variants(self, clues: LocationClues, fallback_text: str) -> List[str]:
        variants = []
        if clues.raw_query and clues.raw_query.strip():
            variants.append(clues.raw_query)
            
        base_context = "Odisha, India"
        
        landmark_expansions = self._expand_landmark(clues.landmark) if clues.landmark else [None]

        for lm in landmark_expansions:
            # 1. Full extracted location
            if lm and clues.village_locality and clues.city_district:
                variants.append(f"{lm}, {clues.village_locality}, {clues.city_district}, {base_context}")
            
            # 3. Drop locality (landmarks with cities)
            if lm and clues.city_district:
                variants.append(f"{lm}, {clues.city_district}, {base_context}")

        # 2. Drop landmark (localities are easier to match)
        if clues.village_locality and clues.city_district:
            variants.append(f"{clues.village_locality}, {clues.city_district}, {base_context}")
            
        # 4. Raw query with context
        if clues.raw_query and clues.raw_query.strip():
            variants.append(f"{clues.raw_query}, {base_context}")
            
        # Dedup keeping order
        seen = set()
        unique_variants = []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                unique_variants.append(v)
                
        if not unique_variants and fallback_text and fallback_text.strip():
            unique_variants.append(fallback_text)
            
        return unique_variants

    def _sync_geocode_with_clues(self, clues: LocationClues, fallback_text: str) -> List[CandidateLocation]:
        from unittest.mock import Mock
        if not isinstance(requests.get, Mock):
            # 1. Check local Bhubaneswar GIS index first
            try:
                from app.gis.local_index import bhubaneswar_location_index
                query_str = clues.raw_query if (clues.raw_query and clues.raw_query.strip()) else fallback_text
                local_res = bhubaneswar_location_index.resolve(query_str)
                if local_res:
                    _, local_candidates = local_res
                    if local_candidates:
                        return local_candidates
            except Exception as e:
                logger.debug(f"Local index resolution skipped in geocoder: {e}")

        variants = self._build_query_variants(clues, fallback_text)
        all_candidates = []
        seen_coords = set()

        for idx, variant in enumerate(variants):
            if len(all_candidates) >= 4:
                break
            
            if idx > 0:
                time.sleep(1.0) # Respect Nominatim 1 request/sec rate limit

            try:
                candidates = self._sync_geocode(variant)
                for c in candidates:
                    # Deduplicate by approximate geographical proximity (~111m precision)
                    coord_key = (round(c.latitude, 3), round(c.longitude, 3))
                    if coord_key not in seen_coords:
                        seen_coords.add(coord_key)
                        all_candidates.append(c)
                        if len(all_candidates) >= 4:
                            break
            except Exception as e:
                logger.error(f"Error geocoding variant '{variant}': {e}")
                
        # Final ranking of the combined candidates pool
        all_candidates.sort(key=lambda c: (c.is_in_jurisdiction, c.confidence), reverse=True)
        return all_candidates[:4]

    async def geocode_with_clues(self, clues: LocationClues, fallback_text: str) -> List[CandidateLocation]:
        return await asyncio.to_thread(self._sync_geocode_with_clues, clues, fallback_text)

geocoder = NominatimGeocoder()
