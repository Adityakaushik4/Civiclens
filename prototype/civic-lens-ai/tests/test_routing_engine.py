import pytest
from app.taxonomy import Category
from app.routing.registry import department_registry
from app.routing.engine import RoutingEngine, RoutingRequest, RoutingStore
from app.database.connection import init_db

def test_routing_registry_waterlogging():
    mapping, reason = department_registry.resolve_routing(Category.DRAINAGE.value, "WATERLOGGING")
    assert mapping.primary_department == "Drainage & Sewerage"
    assert mapping.responsible_unit == "Stormwater & Drain Unit"

def test_routing_registry_pothole():
    mapping, reason = department_registry.resolve_routing(Category.ROAD_DAMAGE.value, "POTHOLE")
    assert mapping.primary_department == "Roads & PWD"
    assert mapping.responsible_unit == "Asphalt Patching Unit"

def test_routing_registry_streetlight():
    mapping, reason = department_registry.resolve_routing(Category.ELECTRICITY.value, "STREETLIGHT")
    assert mapping.primary_department == "Electrical / Street Lighting"
    assert mapping.responsible_unit == "Power Grid Unit"

def test_routing_registry_garbage():
    mapping, reason = department_registry.resolve_routing(Category.GARBAGE.value, "OVERFLOWING_BIN")
    assert mapping.primary_department == "Sanitation & Waste Management"
    assert mapping.responsible_unit == "Solid Waste Management Unit"

def test_routing_engine_actual_function():
    engine = RoutingEngine()
    req = RoutingRequest(
        issue_id="test-123",
        category=Category.DRAINAGE.value,
        subcategory="WATERLOGGING",
        priority_score=80,
        priority_level="HIGH",
        latitude=20.0,
        longitude=85.0
    )
    decision = engine.route_issue(req)
    assert decision.primary_department == "Drainage & Sewerage"
    assert decision.responsible_unit == "Stormwater & Drain Unit"

def test_routing_persistence():
    init_db()
    engine = RoutingEngine()
    store = RoutingStore()
    
    req = RoutingRequest(
        issue_id="test-persistence-456",
        category=Category.DRAINAGE.value,
        subcategory="WATERLOGGING",
        priority_score=80,
        priority_level="HIGH",
        latitude=20.0,
        longitude=85.0
    )
    decision = engine.route_issue(req)
    
    # Save the decision to DB
    store.save(decision)
    
    # Close session
    del store
    
    # New session
    store_reloaded = RoutingStore()
    reloaded_decision = store_reloaded.get("test-persistence-456")
    
    assert reloaded_decision is not None
    assert reloaded_decision.primary_department == "Drainage & Sewerage"
    assert reloaded_decision.responsible_unit == "Stormwater & Drain Unit"
