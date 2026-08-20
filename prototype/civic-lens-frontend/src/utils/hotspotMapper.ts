import type { CivicHotspot } from '../types';
import type { HotspotCircle } from '../components/maps/CivicMap';

/**
 * Validates and maps backend CivicHotspot data to frontend HotspotCircle props for the map.
 * Ensures strict coordinate validation and privacy suppression rules.
 */
export function mapValidPublicHotspots(hotspots: CivicHotspot[] | undefined): HotspotCircle[] {
  if (!hotspots || hotspots.length === 0) {
    return [];
  }

  return hotspots
    .filter(h => {
      // 1. Enforce privacy rules
      if (h.suppressed_publicly === true) {
        return false;
      }

      // 2. Validate coordinates exist and are finite
      const lat = h.center_latitude;
      const lng = h.center_longitude;

      if (lat == null || lng == null) return false;
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;

      // 3. Validate coordinate bounds
      if (lat < -90 || lat > 90) return false;
      if (lng < -180 || lng > 180) return false;

      // 4. Never use [0,0] as a fallback or valid location
      if (lat === 0 && lng === 0) return false;

      return true;
    })
    .map(h => ({
      id: h.hotspot_id,
      lat: h.center_latitude,
      lng: h.center_longitude,
      radius: h.radius_meters || 300,
      score: h.severity_score_weighted || 0,
      count: h.citizen_report_count || 0,
    }));
}
