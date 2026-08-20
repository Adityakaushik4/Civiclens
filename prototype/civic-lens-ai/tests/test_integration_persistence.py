import os
import pytest
import json

from app.database.connection import init_db
from app.duplicates.store import MasterIssueStore, Category
from app.routing.engine import RoutingEngine, RoutingStore, RoutingRequest
from app.escalation.state_machine import EscalationStateMachine, EscalationStore
from app.privacy.transformer import PrivacyTransformer, PublicIssueStore

def test_persistence_full_lifecycle():
    # 1. Initialize DB and stores
    init_db()
    
    ms_store = MasterIssueStore()
    
    # 2. Create Master Issue
    embedding = [0.1, 0.2, 0.3]
    master_issue = ms_store.create_master_issue(
        title="Test Waterlogging",
        category=Category.DRAINAGE,
        subcategory="WATERLOGGING",
        latitude=20.296,
        longitude=85.824,
        severity=3,
        embedding=embedding
    )
    
    # Assert it's in memory
    assert ms_store.get(master_issue.id) is not None
    
    # 3. Force sync to DB (create_master_issue doesn't sync! Wait, does it? Let's check.)
    ms_store._sync_to_db(master_issue)
    
    # 4. Simulate backend restart
    del ms_store
    
    ms_store_reloaded = MasterIssueStore()
    reloaded_issue = ms_store_reloaded.get(master_issue.id)
    
    if reloaded_issue is None:
        pytest.fail("Master issue did not persist to the database!")
        
    assert reloaded_issue.id == master_issue.id
    
    # 5. Check if embedding is properly parsed
    assert isinstance(reloaded_issue.embedding, list)
    
    # 6. Route Issue
    routing_engine = RoutingEngine()
    routing_store = RoutingStore()
    
    request = RoutingRequest(
        issue_id=reloaded_issue.id,
        category="DRAINAGE",
        subcategory="WATERLOGGING",
        priority_score=75,
        priority_level="HIGH",
        latitude=20.296,
        longitude=85.824
    )
    decision = routing_engine.route_issue(request)
    routing_store.save(decision)
    
    # 7. Lifecycle
    escalation_store = EscalationStore()
    escalation_sm = EscalationStateMachine()
    
    lifecycle = escalation_sm.initialize_lifecycle(decision)
    escalation_store.save(lifecycle)
    
    # 8. Public Detail
    public_store = PublicIssueStore()
    privacy_transformer = PrivacyTransformer()
    
    public_view = privacy_transformer.generate_public_view(reloaded_issue.id)
    
    assert public_view.department_name == "Drainage & Sewerage"
    assert public_view.status == "ROUTED"
    assert public_view.category == "DRAINAGE"
