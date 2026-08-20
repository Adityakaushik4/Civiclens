import { describe, it, expect } from 'vitest';
import { mapValidPublicHotspots } from './hotspotMapper';
import type { CivicHotspot } from '../types';

describe('hotspotMapper', () => {
  const baseHotspot: CivicHotspot = {
    hotspot_id: 'hs_1',
    category: 'ROAD_DAMAGE',
    center_latitude: 20.2961,
    center_longitude: 85.8245,
    radius_meters: 500,
    master_issue_count: 1,
    citizen_report_count: 5,
    severity_score_weighted: 3.5,
    vulnerable_location_near: false,
    suppressed_publicly: false,
    linked_master_issue_ids: [],
    created_at: '2026-08-13T16:01:22.000Z'
  };

  it('should correctly map valid public hotspots', () => {
    const result = mapValidPublicHotspots([baseHotspot]);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: 'hs_1',
      lat: 20.2961,
      lng: 85.8245,
      radius: 500,
      score: 3.5,
      count: 5,
    });
  });

  it('should filter out hotspots where suppressed_publicly is true', () => {
    const suppressed = { ...baseHotspot, suppressed_publicly: true, hotspot_id: 'hs_suppressed' };
    const result = mapValidPublicHotspots([baseHotspot, suppressed]);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('hs_1');
  });

  it('should filter out missing coordinates', () => {
    const missingLat = { ...baseHotspot, center_latitude: undefined as any };
    const missingLng = { ...baseHotspot, center_longitude: null as any };
    const result = mapValidPublicHotspots([missingLat, missingLng]);
    expect(result).toHaveLength(0);
  });

  it('should filter out invalid (non-finite) coordinates', () => {
    const invalidLat = { ...baseHotspot, center_latitude: NaN };
    const invalidLng = { ...baseHotspot, center_longitude: Infinity };
    const result = mapValidPublicHotspots([invalidLat, invalidLng]);
    expect(result).toHaveLength(0);
  });

  it('should filter out out-of-bounds coordinates', () => {
    const outOfBoundsLat = { ...baseHotspot, center_latitude: 91 };
    const outOfBoundsLng = { ...baseHotspot, center_longitude: -181 };
    const result = mapValidPublicHotspots([outOfBoundsLat, outOfBoundsLng]);
    expect(result).toHaveLength(0);
  });

  it('should filter out exact [0, 0] coordinates', () => {
    const zeroZero = { ...baseHotspot, center_latitude: 0, center_longitude: 0 };
    const result = mapValidPublicHotspots([zeroZero]);
    expect(result).toHaveLength(0);
  });

  it('should return empty array for undefined or empty list', () => {
    expect(mapValidPublicHotspots(undefined)).toEqual([]);
    expect(mapValidPublicHotspots([])).toEqual([]);
  });
});
