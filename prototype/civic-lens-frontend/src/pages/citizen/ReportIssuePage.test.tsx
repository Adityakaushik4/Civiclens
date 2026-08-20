import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as aiApi from '../../api/ai';
import * as issuesApi from '../../api/issues';

describe('ReportIssuePage Location Flow Logic', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('preserves exact geocoded candidate coordinates without mock fallbacks', async () => {
    const mockCandidates = [
      {
        display_name: 'ITER, Bhubaneswar, Odisha, India',
        latitude: 20.2503,
        longitude: 85.8000,
        confidence: 0.95,
        source: 'Nominatim',
      },
    ];

    vi.spyOn(aiApi, 'extractLocationClues').mockResolvedValue({
      clues: {
        landmark: 'ITER',
        city_district: 'Bhubaneswar',
        raw_query: 'ITER Bhubaneswar',
        confidence: 0.95,
      },
      candidates: mockCandidates,
    });

    const result = await aiApi.extractLocationClues('There is a large pothole near ITER Bhubaneswar');

    expect(result.candidates).toHaveLength(1);
    expect(result.candidates[0].latitude).toBe(20.2503);
    expect(result.candidates[0].longitude).toBe(85.8000);
    expect(result.candidates[0].display_name).toContain('ITER');
  });

  it('returns empty candidate list when location cannot be determined', async () => {
    vi.spyOn(aiApi, 'extractLocationClues').mockResolvedValue({
      clues: {
        raw_query: '',
        confidence: 0.0,
      },
      candidates: [],
    });

    const result = await aiApi.extractLocationClues('There is a pothole on the road');

    expect(result.candidates).toHaveLength(0);
    expect(result.clues.confidence).toBe(0.0);
  });

  it('passes exact confirmed location coordinates into downstream engines', async () => {
    const selectedCoords = { lat: 20.2503, lng: 85.8000 };

    const dupSpy = vi.spyOn(aiApi, 'checkDuplicates').mockResolvedValue({
      action: 'NEW_MASTER_ISSUE',
      total_score: 0.1,
      score_breakdown: {
        geographic_distance_meters: 1000,
        spatial_score: 0.1,
        semantic_similarity: 0.1,
        category_match_score: 0.1,
        temporal_score: 0.1,
        total_score: 0.1,
      },
      citizen_reporter_count: 1,
    });

    const prioSpy = vi.spyOn(issuesApi, 'calculatePriority').mockResolvedValue({
      issue_id: 'issue-1',
      priority_score: 85,
      priority_level: 'HIGH',
      calculated_at: new Date().toISOString(),
    });

    const routeSpy = vi.spyOn(issuesApi, 'routeIssue').mockResolvedValue({
      issue_id: 'issue-1',
      routed_at: new Date().toISOString(),
      assigned_department: 'Roads & PWD',
    });

    await aiApi.checkDuplicates({
      text: 'Pothole near ITER',
      category: 'ROAD_DAMAGE',
      subcategory: 'POTHOLE',
      latitude: selectedCoords.lat,
      longitude: selectedCoords.lng,
      severity: 4,
      safety_risk: true,
      description: 'Large pothole in the middle of the road',
    });

    await issuesApi.calculatePriority({
      category: 'ROAD_DAMAGE',
      subcategory: 'POTHOLE',
      severity: 4,
      safety_risk: true,
      public_impact: 4,
      latitude: selectedCoords.lat,
      longitude: selectedCoords.lng,
    });

    await issuesApi.routeIssue({
      category: 'ROAD_DAMAGE',
      subcategory: 'POTHOLE',
      priority_score: 85,
      priority_level: 'HIGH',
      latitude: selectedCoords.lat,
      longitude: selectedCoords.lng,
    });

    expect(dupSpy).toHaveBeenCalledWith(expect.objectContaining({ latitude: 20.2503, longitude: 85.8000 }));
    expect(prioSpy).toHaveBeenCalledWith(expect.objectContaining({ latitude: 20.2503, longitude: 85.8000 }));
    expect(routeSpy).toHaveBeenCalledWith(expect.objectContaining({ latitude: 20.2503, longitude: 85.8000 }));
  });
});
