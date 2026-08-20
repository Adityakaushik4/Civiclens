import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    VisualAnalysis,
    ComplaintAnalysis,
    Category,
    ConfidenceStatus,
)
from app.vision.base import VisionProvider, VisionProviderError, VisionInvalidImageError

client = TestClient(app)


def generate_synthetic_png_bytes(size_bytes: int = 128) -> bytes:
    """Generate a minimal valid 1x1 pixel PNG file header + payload."""
    # 67-byte minimal valid PNG file binary header
    png_header = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    if size_bytes > len(png_header):
        padding = b"\x00" * (size_bytes - len(png_header))
        return bytes(png_header + padding)
    return bytes(png_header)


class MockVisionProvider(VisionProvider):
    def __init__(
        self,
        visible_issue=True,
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        severity=4,
        safety_risk=True,
        public_impact=4,
        description="Large pothole on roadway",
        confidence=0.91,
        disagreement=False,
        disagreement_reason=None,
        raise_error=None
    ):
        self.visible_issue = visible_issue
        self.category = category
        self.subcategory = subcategory
        self.severity = severity
        self.safety_risk = safety_risk
        self.public_impact = public_impact
        self.description = description
        self.confidence = confidence
        self.disagreement = disagreement
        self.disagreement_reason = disagreement_reason
        self.raise_error = raise_error

    async def analyze_image(self, file_path: str, mime_type: str, optional_text: str = None):
        if self.raise_error:
            raise self.raise_error

        v_analysis = VisualAnalysis(
            visible_issue=self.visible_issue,
            category=self.category,
            subcategory=self.subcategory,
            severity=self.severity,
            safety_risk=self.safety_risk,
            public_impact=self.public_impact,
            description=self.description,
            confidence=self.confidence
        )

        has_text = bool(optional_text and optional_text.strip())

        if has_text:
            clean_text = optional_text.strip()
            # Rule mapping for mock provider test execution (specific issues before generic 'road')
            text_lower = clean_text.lower()
            if "light" in text_lower or "bulb" in text_lower or "street light" in text_lower:
                text_cat, text_sub, default_text_sev = Category.STREETLIGHT, "LIGHT_OUT", 3
            elif "garbage" in text_lower or "trash" in text_lower or "dumped" in text_lower:
                text_cat, text_sub, default_text_sev = Category.GARBAGE, "UNCOLLECTED_GARBAGE", 3
            elif "pothole" in text_lower or "road" in text_lower:
                text_cat, text_sub, default_text_sev = Category.ROAD_DAMAGE, "POTHOLE", 4
            else:
                text_cat, text_sub, default_text_sev = Category.OTHER, "GENERAL", 2

            if text_cat == self.category:
                disagreement = False
                disagreement_reason = None
                final_sev = max(default_text_sev, self.severity) if self.visible_issue else default_text_sev
            else:
                disagreement = True
                text_cat_label = text_cat.value.lower().replace("_", " ")
                vis_cat_label = self.category.value.lower().replace("_", " ")
                disagreement_reason = (
                    f"Citizen reported a {text_cat_label} issue, while the uploaded image "
                    f"visibly shows {vis_cat_label} and does not clearly verify the {text_cat_label}."
                )
                final_sev = default_text_sev

            c_analysis = ComplaintAnalysis(
                original_text=clean_text,
                original_language="en",
                normalized_text=clean_text,
                language="en",
                category=text_cat,
                subcategory=text_sub,
                severity=final_sev,
                safety_risk=self.safety_risk,
                public_impact=self.public_impact,
                location_description="on roadway",
                summary=clean_text,
                confidence=self.confidence,
                confidence_status=ConfidenceStatus.ACCEPTED if self.confidence >= 0.8 else ConfidenceStatus.LOW_CONFIDENCE,
                language_confidence=1.0,
                language_detector="latin_script_heuristic",
                language_disagreement=False
            )
            return v_analysis, c_analysis, disagreement, disagreement_reason
        else:
            c_analysis = ComplaintAnalysis(
                original_text=self.description,
                original_language="en",
                normalized_text=self.description,
                language="en",
                category=self.category,
                subcategory=self.subcategory,
                severity=self.severity,
                safety_risk=self.safety_risk,
                public_impact=self.public_impact,
                location_description="on roadway",
                summary=self.description,
                confidence=self.confidence,
                confidence_status=ConfidenceStatus.ACCEPTED if self.confidence >= 0.8 else ConfidenceStatus.LOW_CONFIDENCE,
                language_confidence=1.0,
                language_detector="latin_script_heuristic",
                language_disagreement=False
            )
            return v_analysis, c_analysis, False, None


# ---------------------------------------------------------
# Vision Endpoint Unit Tests
# ---------------------------------------------------------

def test_invalid_image_extension():
    files = {"file": ("test.pdf", b"%PDF-1.4 dummy data", "application/pdf")}
    response = client.post("/api/v1/ai/analyze-image", files=files)
    assert response.status_code == 415
    assert "Unsupported Image Format" in response.json()["error"]


def test_empty_image_file():
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post("/api/v1/ai/analyze-image", files=files)
    assert response.status_code == 400
    assert "Empty Image File" in response.json()["error"]


def test_oversized_image_file():
    large_payload = b"\x00" * (11 * 1024 * 1024)
    files = {"file": ("huge.png", large_payload, "image/png")}
    response = client.post("/api/v1/ai/analyze-image", files=files)
    assert response.status_code == 413
    assert "Oversized Image File" in response.json()["error"]


def test_vision_provider_failure():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("pothole.png", png_data, "image/png")}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(raise_error=VisionProviderError("Vision API Offline"))
        response = client.post("/api/v1/ai/analyze-image", files=files)
        assert response.status_code == 503
        assert response.json()["error"] == "Vision Provider Error"


def test_pothole_image_analysis():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("pothole.png", png_data, "image/png")}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            description="Deep pothole in middle of road"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["input_type"] == "image"
        assert res["visual_analysis"]["visible_issue"] is True
        assert res["visual_analysis"]["category"] == "ROAD_DAMAGE"
        assert res["visual_analysis"]["subcategory"] == "POTHOLE"
        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["evidence_disagreement"] is False


def test_garbage_image_analysis():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE",
            description="Overflowing garbage dump"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["visual_analysis"]["subcategory"] == "UNCOLLECTED_GARBAGE"


def test_drainage_image_analysis():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("drainage.png", png_data, "image/png")}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.DRAINAGE,
            subcategory="BLOCKED_DRAIN",
            description="Clogged open drain with stagnant water"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["visual_analysis"]["category"] == "DRAINAGE"
        assert res["visual_analysis"]["subcategory"] == "BLOCKED_DRAIN"


def test_irrelevant_non_civic_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("cat.png", png_data, "image/png")}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            visible_issue=False,
            category=Category.OTHER,
            subcategory="GENERAL_CIVIC_ISSUE",
            severity=0,
            public_impact=0,
            description="Indoor household cat picture",
            confidence=0.2
        )
        response = client.post("/api/v1/ai/analyze-image", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["visual_analysis"]["visible_issue"] is False
        assert res["visual_analysis"]["category"] == "OTHER"
        assert res["analysis"]["confidence_status"] == "LOW_CONFIDENCE"


# ---------------------------------------------------------
# Required Regression Tests for Citizen Precedence Rule
# ---------------------------------------------------------

def test_1_text_plus_matching_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("pothole.png", png_data, "image/png")}
    data = {"text": "There is a large pothole on the road."}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["visual_analysis"]["category"] == "ROAD_DAMAGE"
        assert res["evidence_disagreement"] is False


def test_2_text_plus_conflicting_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}
    data = {"text": "There is a street light issue here"}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE",
            description="Overflowing roadside garbage dump"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "STREETLIGHT"
        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["evidence_disagreement"] is True
        assert "streetlight" in res["disagreement_reason"].lower()


def test_3_text_only():
    async def mock_extract_structured(self, text: str, language: str, retry_prompt=None):
        return {
            "category": "STREETLIGHT",
            "subcategory": "LIGHT_OUT",
            "severity": 3,
            "safety_risk": False,
            "public_impact": 3,
            "summary": text,
            "confidence": 0.95
        }

    with patch("app.llm.gemini_provider.GeminiLLMProvider.extract_structured", side_effect=mock_extract_structured, autospec=True):
        response = client.post("/api/v1/ai/analyze", json={"text": "There is a broken streetlight near my house."})
        assert response.status_code == 200
        res = response.json()
        assert res["category"] == "STREETLIGHT"


def test_4_image_only():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "GARBAGE"
        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["evidence_disagreement"] is False


def test_5_garbage_text_plus_garbage_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}
    data = {"text": "There is garbage dumped beside the road."}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "GARBAGE"
        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["evidence_disagreement"] is False


def test_6_mandatory_streetlight_text_plus_garbage_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}
    data = {"text": "There is a street light issue here"}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE",
            description="Dark roadside drainage with visible garbage"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "STREETLIGHT"
        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["evidence_disagreement"] is True
        assert res["disagreement_reason"] is not None


def test_7_road_damage_text_plus_unrelated_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}
    data = {"text": "There is a huge pothole on the road"}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["evidence_disagreement"] is True


def test_8_empty_text_plus_image():
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("road.png", png_data, "image/png")}
    data = {"text": "   "}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["evidence_disagreement"] is False


def test_9_existing_issue_creation():
    png_data = generate_synthetic_png_bytes()
    files = {"photo": ("light.png", png_data, "image/png")}
    data = {
        "category": "STREETLIGHT",
        "subcategory": "LIGHT_OUT",
        "priority_score": "3",
        "priority_level": "MEDIUM",
        "latitude": "20.2961",
        "longitude": "85.8245"
    }
    response = client.post("/api/v1/issues/citizen-report", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert "issue_id" in res
    assert "decision_id" in res


def test_10_existing_category_routing():
    data = {
        "issue_id": "test_issue_123",
        "category": "STREETLIGHT",
        "subcategory": "LIGHT_OUT",
        "priority_score": 3,
        "priority_level": "MEDIUM"
    }
    response = client.post("/api/v1/routing/route", json=data)
    assert response.status_code == 200
    res = response.json()
    assert res["primary_department"] == "Electrical / Street Lighting"


def test_11_existing_location_extraction_behavior():
    response = client.post("/api/v1/ai/extract-location", json={"text": "Waterlogging near Nayapalli, Bhubaneswar"})
    assert response.status_code == 200
    res = response.json()
    assert res["candidates"] is not None


def test_12_differing_categories_severity_rules():
    """
    Test SEVERITY RULES:
    When citizen text ('streetlight is not working', severity 3) and visual evidence ('garbage accumulation', visual severity 5)
    describe DIFFERENT categories:
    - Primary category = STREETLIGHT
    - Primary severity = 3 (text severity, NOT increased to 5)
    - Visual category = GARBAGE
    - Visual severity = 5
    - evidence_disagreement = True
    """
    png_data = generate_synthetic_png_bytes()
    files = {"file": ("garbage.png", png_data, "image/png")}
    data = {"text": "streetlight is not working"}

    with patch("app.main.get_vision_provider") as mock_factory:
        mock_factory.return_value = MockVisionProvider(
            category=Category.GARBAGE,
            subcategory="UNCOLLECTED_GARBAGE",
            severity=5,
            description="Massive overflowing garbage dump"
        )
        response = client.post("/api/v1/ai/analyze-image", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["analysis"]["category"] == "STREETLIGHT"
        assert res["analysis"]["severity"] == 3
        assert res["visual_analysis"]["category"] == "GARBAGE"
        assert res["visual_analysis"]["severity"] == 5
        assert res["evidence_disagreement"] is True




