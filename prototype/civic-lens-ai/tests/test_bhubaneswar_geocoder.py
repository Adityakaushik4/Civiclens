import pytest
import asyncio
import os
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.gis.local_index import bhubaneswar_location_index
from app.gis.normalizer import extract_location_phrases, apply_phonetic_normalization


def test_phonetic_normalization():
    assert apply_phonetic_normalization("bhubneshwar") == "bhubaneswar"
    assert apply_phonetic_normalization("bhubneswar") == "bhubaneswar"
    assert apply_phonetic_normalization("bhubaneshwar") == "bhubaneswar"
    assert apply_phonetic_normalization("jayadev vihar") == "jaydev vihar"
    assert apply_phonetic_normalization("sahid nagar") == "saheed nagar"


def test_phrase_extraction_from_complaints():
    text = "There is a large pothole near Silicon Institute, Bhubaneswar"
    phrases = extract_location_phrases(text)
    assert any("silicon" in p for p in phrases)
    assert any("silicon institute" in p for p in phrases)


def test_local_index_bhubaneswar_spellings():
    for query in ["Bhubaneswar", "bhubneshwar", "Bhubneswar", "bhubaneshwar"]:
        res = bhubaneswar_location_index.resolve(query)
        assert res is not None, f"Failed to resolve {query}"
        clues, candidates = res
        assert len(candidates) > 0
        cand = candidates[0]
        assert "Bhubaneswar" in cand.display_name
        assert 20.20 <= cand.latitude <= 20.35
        assert 85.75 <= cand.longitude <= 85.90
        assert cand.confidence >= 0.85
        assert cand.is_in_jurisdiction is True
        assert cand.source == "LocalBhubaneswarIndex"


def test_local_index_silicon_aliases():
    queries = [
        "Silicon",
        "Silicon Institute",
        "Silicon University",
        "Silicon Bhubaneswar",
        "Silicon Institute of Technology"
    ]
    for q in queries:
        res = bhubaneswar_location_index.resolve(q)
        assert res is not None, f"Failed to resolve {q}"
        clues, candidates = res
        assert len(candidates) > 0
        cand = candidates[0]
        assert "Silicon University" in cand.display_name
        assert abs(cand.latitude - 20.3504) < 0.01
        assert abs(cand.longitude - 85.8065) < 0.01
        assert cand.confidence >= 0.85
        assert cand.is_in_jurisdiction is True


def test_local_index_prominent_landmarks():
    cases = [
        ("KIIT", "Kalinga Institute of Industrial Technology (KIIT)"),
        ("ITER", "Institute of Technical Education and Research (ITER / SOA)"),
        ("Patia", "Patia"),
        ("Khandagiri", "Khandagiri"),
        ("Jaydev Vihar", "Jaydev Vihar"),
        ("Master Canteen", "Master Canteen"),
        ("SUM Hospital", "IMS and SUM Hospital"),
        ("AIIMS Bhubaneswar", "AIIMS Bhubaneswar"),
        ("CV Raman", "C. V. Raman Global University"),
        ("CVRGU", "C. V. Raman Global University"),
        ("C. V. Raman", "C. V. Raman Global University"),
        ("BMC Bhawan", "Bhubaneswar Municipal Corporation (BMC HQ)"),
        ("Secretariat", "Lok Seva Bhawan (Odisha Secretariat)"),
        ("Lok Seva Bhawan", "Lok Seva Bhawan (Odisha Secretariat)"),
        ("Vidhan Sabha", "Odisha Legislative Assembly (Vidhan Sabha)"),
        ("Airport", "Biju Patnaik International Airport"),
        ("BBSR Airport", "Biju Patnaik International Airport"),
        ("IIT Bhubaneswar", "IIT Bhubaneswar"),
        ("IIT BBSR", "IIT Bhubaneswar"),
        ("AG Square", "AG Square (AG Chhak)"),
        ("AG Chhak", "AG Square (AG Chhak)"),
        ("CRPF Square", "CRPF Square (CRPF Chhak)"),
        ("CRPF Chhak", "CRPF Square (CRPF Chhak)"),
        ("Kalinga Stadium", "Kalinga Stadium"),
        ("Hi-Tech Hospital", "Hi-Tech Medical College & Hospital"),
        ("Janpath", "Janpath Road"),
        ("Dumduma", "Dumduma Housing Board"),
        ("Sailashree Vihar", "Sailashree Vihar"),
        ("Rajarani Temple", "Rajarani Temple"),
        ("Planetarium", "Pathani Samanta Planetarium"),
        ("Ekamra Kanan", "Ekamra Kanan Botanical Park"),
    ]
    for q, expected_name in cases:
        res = bhubaneswar_location_index.resolve(q)
        assert res is not None, f"Failed to resolve {q}"
        _, candidates = res
        assert expected_name in candidates[0].display_name
        assert candidates[0].confidence >= 0.85


def test_complaint_sentence_extraction():
    text = "There is a severe pothole near Silicon Institute, Bhubaneswar"
    res = bhubaneswar_location_index.resolve(text)
    assert res is not None
    clues, candidates = res
    assert "Silicon University" in candidates[0].display_name
    assert candidates[0].confidence >= 0.85


def test_cvrgu_complaint_sentence_resolution():
    text = "Open drain waterlogging in front of C. V. Raman Global University, Bhubaneswar"
    res = bhubaneswar_location_index.resolve(text)
    assert res is not None
    clues, candidates = res
    assert "C. V. Raman Global University" in candidates[0].display_name
    assert candidates[0].confidence >= 0.85
    assert candidates[0].is_in_jurisdiction is True


def test_generic_complaint_falls_through_safely():
    # A generic complaint with no recognizable POI or locality should return None from local index
    text = "The road beside the big market near the university is flooded"
    res = bhubaneswar_location_index.resolve(text)
    assert res is None, "Generic complaint should not falsely match a local landmark"


@pytest.mark.asyncio
async def test_extract_location_endpoint_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test 1: Renowned location with alias & spelling variation
        response = await ac.post(
            "/api/v1/ai/extract-location",
            json={"text": "Large pothole in front of Silicon Institute, bhubneshwar"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "clues" in data
        assert "candidates" in data
        assert len(data["candidates"]) > 0
        first_cand = data["candidates"][0]
        assert "Silicon University" in first_cand["display_name"]
        assert first_cand["source"] == "LocalBhubaneswarIndex"
        assert first_cand["confidence"] >= 0.85
        assert first_cand["is_in_jurisdiction"] is True

        # Test 2: Standard city name spelling variation
        resp2 = await ac.post(
            "/api/v1/ai/extract-location",
            json={"text": "bhubneshwar"}
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["candidates"]) > 0
        assert "Bhubaneswar" in data2["candidates"][0]["display_name"]

        # Test 3: Newly added P0 entity: C. V. Raman Global University
        resp3 = await ac.post(
            "/api/v1/ai/extract-location",
            json={"text": "Broken streetlight near CVRGU"}
        )
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert len(data3["candidates"]) > 0
        assert "C. V. Raman Global University" in data3["candidates"][0]["display_name"]


def test_reverse_resolve_coordinates_human_readable_name():
    # 1. CVRGU exact coordinates -> C. V. Raman Global University
    res1 = bhubaneswar_location_index.reverse_resolve_coordinates(20.2198, 85.7358)
    assert res1 is not None
    assert res1["canonical_name"] == "C. V. Raman Global University"

    # 2. KIIT coordinates -> Kalinga Institute of Industrial Technology (KIIT)
    res2 = bhubaneswar_location_index.reverse_resolve_coordinates(20.3533, 85.8193)
    assert res2 is not None
    assert "KIIT" in res2["canonical_name"] or "Kalinga Institute" in res2["canonical_name"]

    # 3. Remote coordinates outside registry radius -> None (triggers fallback)
    res3 = bhubaneswar_location_index.reverse_resolve_coordinates(20.5000, 86.1000)
    assert res3 is None


def test_privacy_transformer_human_readable_title():
    from app.privacy.transformer import privacy_transformer
    from app.duplicates import master_issue_store, MasterIssueRecord
    from app.schemas import Category

    # Create dummy master issue record near CVRGU coordinates
    rec1 = MasterIssueRecord(
        id="CIVIC-TEST-CVRGU",
        title="Waterlogging issue",
        category=Category.DRAINAGE,
        subcategory="WATERLOGGING",
        severity_score=1,
        latitude=20.2198,
        longitude=85.7358,
        description="Near Mahura"
    )
    master_issue_store.add(rec1)

    view = privacy_transformer.generate_public_view("CIVIC-TEST-CVRGU")
    assert view.public_location_description == "C. V. Raman Global University"
    assert view.fuzzed_latitude == 20.220
    assert view.fuzzed_longitude == 85.736

    # Test fallback for remote issue coordinates
    rec2 = MasterIssueRecord(
        id="CIVIC-TEST-REMOTE",
        title="Remote road issue",
        category=Category.ROAD_DAMAGE,
        subcategory="POTHOLE",
        severity_score=1,
        latitude=20.5000,
        longitude=86.1000,
        description="Remote road"
    )
    master_issue_store.add(rec2)

    remote_view = privacy_transformer.generate_public_view("CIVIC-TEST-REMOTE")
    assert "Municipal Zone Area" in remote_view.public_location_description
    assert "20.5" in remote_view.public_location_description




