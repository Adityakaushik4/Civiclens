import pytest
from app.analytics.hotspots import hotspot_engine, hotspot_store
from app.opportunities.engine import opportunity_engine, opportunity_store

def test_hotspot_deduplication():
    # Run hotspot detection once
    initial_hotspots = hotspot_engine.detect_hotspots()
    initial_count = len(hotspot_store.list_all())
    
    assert initial_count > 0, "Should generate at least one hotspot"
    
    # Run hotspot detection again
    second_hotspots = hotspot_engine.detect_hotspots()
    second_count = len(hotspot_store.list_all())
    
    assert second_count == initial_count, f"Hotspot count increased from {initial_count} to {second_count}! Deduplication failed."
    assert len(initial_hotspots) == len(second_hotspots), "Detection returned a different number of hotspots."
    
    # Assert stable IDs are the same
    initial_ids = set(hs.hotspot_id for hs in initial_hotspots)
    second_ids = set(hs.hotspot_id for hs in second_hotspots)
    
    assert initial_ids == second_ids, "Stable IDs changed between runs!"

def test_opportunity_deduplication():
    # Ensure hotspots are present
    hotspot_engine.detect_hotspots()
    
    # Run opportunity detection once
    initial_opps = opportunity_engine.detect_opportunities()
    initial_count = len(opportunity_store.list_all())
    
    assert initial_count > 0, "Should generate at least one opportunity"
    
    # Run opportunity detection again
    second_opps = opportunity_engine.detect_opportunities()
    second_count = len(opportunity_store.list_all())
    
    assert second_count == initial_count, f"Opportunity count increased from {initial_count} to {second_count}! Deduplication failed."
    assert len(initial_opps) == len(second_opps), "Detection returned a different number of opportunities."
    
    # Assert stable IDs are the same
    initial_ids = set(opp.opportunity_id for opp in initial_opps)
    second_ids = set(opp.opportunity_id for opp in second_opps)
    
    assert initial_ids == second_ids, "Stable IDs changed between runs!"
