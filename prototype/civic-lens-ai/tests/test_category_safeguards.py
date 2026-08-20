import pytest
import os
import tempfile
from PIL import Image

from app.pipeline import ComplaintEnginePipeline
from app.taxonomy import Category
from app.gis.local_index import bhubaneswar_location_index
from app.vision.gemini_vision import GeminiVisionProvider


@pytest.mark.asyncio
async def test_1_streetlight_issue_classification():
    pipeline = ComplaintEnginePipeline()
    res = await pipeline.process("streetlight issue")
    assert res.category == Category.STREETLIGHT


@pytest.mark.asyncio
async def test_2_street_light_is_not_working():
    pipeline = ComplaintEnginePipeline()
    res = await pipeline.process("street light is not working")
    assert res.category == Category.STREETLIGHT


@pytest.mark.asyncio
async def test_3_street_lamp_broken_near_cv_raman():
    pipeline = ComplaintEnginePipeline()
    res = await pipeline.process("street lamp broken near CV Raman")
    assert res.category == Category.STREETLIGHT

    # Verify location resolver resolves CV Raman independently
    loc_res = bhubaneswar_location_index.resolve("street lamp broken near CV Raman")
    assert loc_res is not None
    clues, candidates = loc_res
    assert "C. V. Raman Global University" in candidates[0].display_name
    # Category in text analysis remains STREETLIGHT
    assert res.category == Category.STREETLIGHT


@pytest.mark.asyncio
async def test_4_garbage_near_cv_raman():
    pipeline = ComplaintEnginePipeline()
    res = await pipeline.process("garbage near CV Raman")
    assert res.category == Category.GARBAGE

    loc_res = bhubaneswar_location_index.resolve("garbage near CV Raman")
    assert loc_res is not None
    clues, candidates = loc_res
    assert "C. V. Raman Global University" in candidates[0].display_name
    assert res.category == Category.GARBAGE


@pytest.mark.asyncio
async def test_5_waterlogging_near_cv_raman():
    pipeline = ComplaintEnginePipeline()
    res = await pipeline.process("waterlogging near CV Raman")
    assert res.category == Category.DRAINAGE

    loc_res = bhubaneswar_location_index.resolve("waterlogging near CV Raman")
    assert loc_res is not None
    clues, candidates = loc_res
    assert "C. V. Raman Global University" in candidates[0].display_name
    assert res.category == Category.DRAINAGE


@pytest.mark.asyncio
async def test_6_pothole_near_kalinga_stadium():
    pipeline = ComplaintEnginePipeline()
    res = await pipeline.process("pothole near Kalinga Stadium")
    assert res.category == Category.ROAD_DAMAGE

    loc_res = bhubaneswar_location_index.resolve("pothole near Kalinga Stadium")
    assert loc_res is not None
    clues, candidates = loc_res
    assert "Kalinga Stadium" in candidates[0].display_name
    assert res.category == Category.ROAD_DAMAGE


@pytest.mark.asyncio
async def test_7_text_intent_precedence_with_image_disagreement(monkeypatch):
    # Mock Gemini Vision to return GARBAGE visual analysis
    class MockVisionProvider(GeminiVisionProvider):
        def __init__(self):
            pass

        async def analyze_image(self, file_path: str, mime_type: str, optional_text: str = None):
            from app.schemas import VisualAnalysis
            vis = VisualAnalysis(
                visible_issue=True,
                category=Category.GARBAGE,
                subcategory="UNCOLLECTED_GARBAGE",
                severity=4,
                safety_risk=False,
                public_impact=3,
                description="Garbage pile visible",
                confidence=0.9
            )
            clean_text = optional_text.strip()
            pipeline = ComplaintEnginePipeline()
            text_analysis = await pipeline.process(clean_text)

            disagreement = text_analysis.category != vis.category
            reason = "Citizen reported streetlight issue but image shows garbage"
            return vis, text_analysis, disagreement, reason

    img = Image.new('RGB', (100, 100), color='green')
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img.save(tmp.name)
        tmp_path = tmp.name

    try:
        provider = MockVisionProvider()
        vis, comp, disagreement, reason = await provider.analyze_image(
            file_path=tmp_path,
            mime_type="image/jpeg",
            optional_text="There is a streetlight issue"
        )
        assert comp.category == Category.STREETLIGHT
        assert vis.category == Category.GARBAGE
        assert disagreement is True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.asyncio
async def test_8_image_only_garbage_complaint(monkeypatch):
    class MockVisionProvider(GeminiVisionProvider):
        def __init__(self):
            pass

        async def analyze_image(self, file_path: str, mime_type: str, optional_text: str = None):
            from app.schemas import VisualAnalysis, ComplaintAnalysis, ConfidenceStatus
            vis = VisualAnalysis(
                visible_issue=True,
                category=Category.GARBAGE,
                subcategory="UNCOLLECTED_GARBAGE",
                severity=3,
                safety_risk=False,
                public_impact=3,
                description="Garbage bin overflow",
                confidence=0.9
            )
            comp = ComplaintAnalysis(
                original_text="Garbage bin overflow",
                original_language="en",
                normalized_text="Garbage bin overflow",
                language="en",
                category=Category.GARBAGE,
                subcategory="UNCOLLECTED_GARBAGE",
                severity=3,
                safety_risk=False,
                public_impact=3,
                summary="Garbage bin overflow",
                confidence=0.9,
                confidence_status=ConfidenceStatus.ACCEPTED
            )
            return vis, comp, False, None

    img = Image.new('RGB', (100, 100), color='blue')
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img.save(tmp.name)
        tmp_path = tmp.name

    try:
        provider = MockVisionProvider()
        vis, comp, disagreement, reason = await provider.analyze_image(
            file_path=tmp_path,
            mime_type="image/jpeg",
            optional_text=None
        )
        assert comp.category == Category.GARBAGE
        assert disagreement is False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_9_generic_location_query_does_not_become_issue_category():
    # Generic civic query in location search should return None, not a location
    res = bhubaneswar_location_index.resolve("streetlight issue")
    assert res is None


def test_10_location_extraction_does_not_modify_category():
    # Extracting location should return location clues, but never touch issue category
    res = bhubaneswar_location_index.resolve("pothole near Kalinga Stadium")
    assert res is not None
    clues, candidates = res
    assert candidates[0].display_name != "Category.ROAD_DAMAGE"
    assert "Kalinga Stadium" in candidates[0].display_name
