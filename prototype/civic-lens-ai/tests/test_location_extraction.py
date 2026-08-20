import pytest
from unittest.mock import AsyncMock, patch
from app.schemas import LocationExtractionRequest, LocationClues
from app.gis.geocoder import NominatimGeocoder, GeocoderError
from app.main import app
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_extract_location_success():
    mock_clues = {
        "village_locality": "Khandia",
        "ward": None,
        "road_street": "Main Road",
        "landmark": "Bus Stop",
        "city_district": "Bhubaneswar",
        "raw_query": "Khandia Bus Stop, Main Road, Bhubaneswar",
        "confidence": 0.85
    }

    mock_candidates = [
        {
            "display_name": "Khandia Bus Stop, Main Road, Bhubaneswar",
            "latitude": 20.2961,
            "longitude": 85.8245,
            "confidence": 0.85,
            "source": "Nominatim"
        }
    ]

    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = mock_clues
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_candidates

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/ai/extract-location",
                    json={"text": "Pothole near Khandia Bus Stop, Main Road, Bhubaneswar"}
                )

            assert response.status_code == 200
            data = response.json()
            assert data["clues"]["village_locality"] == "Khandia"
            assert data["clues"]["raw_query"] == "Khandia Bus Stop, Main Road, Bhubaneswar"
            assert len(data["candidates"]) == 1
            assert data["candidates"][0]["latitude"] == 20.2961

@pytest.mark.asyncio
async def test_extract_location_empty_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/ai/extract-location", json={"text": "   "})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_geocoder_sync():
    geocoder = NominatimGeocoder()
    with patch("requests.get") as mock_get:
        mock_response = mock_get.return_value
        mock_response.json.return_value = [
            {
                "display_name": "Test Place, Bhubaneswar, Odisha, India",
                "lat": "20.2961",
                "lon": "85.8245",
                "importance": 0.5,
                "address": {"city": "Bhubaneswar", "state": "Odisha", "country": "India"}
            }
        ]
        mock_response.raise_for_status.return_value = None

        candidates = geocoder._sync_geocode("Test Place")
        assert len(candidates) == 1
        assert candidates[0].latitude == 20.2961
        assert candidates[0].longitude == 85.8245
        assert candidates[0].display_name == "Test Place, Bhubaneswar, Odisha, India"
        assert candidates[0].confidence >= 0.90
        assert candidates[0].is_in_jurisdiction is True

@pytest.mark.asyncio
async def test_jurisdiction_aware_geocoding_ambiguous_landmark():
    """
    Regression Test: Ambiguous landmark search 'ITER' returning both a foreign candidate (France)
    and a local candidate (Bhubaneswar, Odisha).
    Verifies that jurisdiction-aware scoring ranks the local candidate #1 with high confidence (>90%)
    and flags the foreign candidate as outside service area (is_in_jurisdiction=False).
    """
    geocoder = NominatimGeocoder()
    mock_raw_nominatim = [
        {
            "display_name": "ITER, Saint-Paul-lès-Durance, Aix-en-Provence, France",
            "lat": "43.7071305",
            "lon": "5.7775861",
            "importance": 0.08005,
            "address": {"village": "Saint-Paul-lès-Durance", "country": "France"}
        },
        {
            "display_name": "ITER, Shanti Vihar Road, Ward 50, Bhubaneswar Municipal Corporation, Bhubaneswar, Khordha, Odisha, 751020, India",
            "lat": "20.2502972",
            "lon": "85.8000303",
            "importance": 0.00006,
            "address": {
                "amenity": "ITER",
                "road": "Shanti Vihar Road",
                "city": "Bhubaneswar Municipal Corporation",
                "state": "Odisha",
                "country": "India"
            }
        }
    ]

    with patch("requests.get") as mock_get:
        mock_response = mock_get.return_value
        mock_response.json.return_value = mock_raw_nominatim
        mock_response.raise_for_status.return_value = None

        candidates = geocoder._sync_geocode("ITER")

        # Must return 2 candidates
        assert len(candidates) == 2

        # Candidate #1 (Ranked First) MUST be the local Bhubaneswar candidate
        top = candidates[0]
        assert "Bhubaneswar" in top.display_name
        assert top.latitude == 20.2502972
        assert top.longitude == 85.8000303
        assert top.confidence >= 0.90
        assert top.is_in_jurisdiction is True

        # Candidate #2 MUST be the foreign France candidate
        foreign = candidates[1]
        assert "France" in foreign.display_name
        assert foreign.is_in_jurisdiction is False
        assert foreign.confidence < top.confidence

@pytest.mark.asyncio
async def test_regression_zero_candidates_no_fake_pin():
    # Proves D: Zero candidates do not create a fake/random pin
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": "Unknown",
            "ward": None,
            "road_street": None,
            "landmark": None,
            "city_district": "Unknown",
            "raw_query": "Unknown",
            "confidence": 0.0
        }
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = [] # Zero candidates
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/ai/extract-location", json={"text": "Unknown location"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["candidates"] == [] # Exactly empty, no fake pins

@pytest.mark.asyncio
async def test_regression_candidate_coordinates_and_confidence_preserved():
    # Proves A, B, C, F: Real candidates passed exactly, coordinates preserved exactly, confidence correct, multiple allowed
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": "ITER",
            "ward": None,
            "road_street": None,
            "landmark": None,
            "city_district": "Bhubaneswar",
            "raw_query": "ITER Bhubaneswar",
            "confidence": 0.8
        }
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = [
                {
                    "display_name": "ITER College",
                    "latitude": 20.2502972,
                    "longitude": 85.8000303,
                    "confidence": 0.00006, # 0% in UI
                    "source": "Nominatim"
                },
                {
                    "display_name": "Jaydev Vihar Flyover",
                    "latitude": 20.2945,
                    "longitude": 85.8236,
                    "confidence": 0.053,
                    "source": "Nominatim"
                }
            ]
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/ai/extract-location", json={"text": "ITER Bhubaneswar"})
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["candidates"]) == 2 # Multiple candidates
            
            # Exact coordinate preservation
            assert data["candidates"][0]["latitude"] == 20.2502972
            assert data["candidates"][0]["longitude"] == 85.8000303
            assert data["candidates"][0]["confidence"] == 0.00006
            
            assert data["candidates"][1]["latitude"] == 20.2945
            assert data["candidates"][1]["longitude"] == 85.8236
            assert data["candidates"][1]["confidence"] == 0.053

@pytest.mark.asyncio
async def test_edge_case_1_named_landmark():
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": None,
            "ward": None,
            "road_street": None,
            "landmark": "ITER College",
            "city_district": "Bhubaneswar",
            "raw_query": "ITER Bhubaneswar",
            "confidence": 0.95
        }
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = [
                {
                    "display_name": "ITER, Jagamara, Bhubaneswar, Khordha, Odisha, India",
                    "latitude": 20.2503,
                    "longitude": 85.8000,
                    "confidence": 0.95,
                    "source": "Nominatim"
                }
            ]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/ai/extract-location", json={"text": "There is a large pothole near ITER Bhubaneswar"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["clues"]["raw_query"] == "ITER Bhubaneswar"
            assert data["candidates"][0]["display_name"] == "ITER, Jagamara, Bhubaneswar, Khordha, Odisha, India"
            assert data["candidates"][0]["latitude"] == 20.2503

@pytest.mark.asyncio
async def test_edge_case_2_local_area():
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": "Jaydev Vihar",
            "ward": None,
            "road_street": None,
            "landmark": None,
            "city_district": "Bhubaneswar",
            "raw_query": "Jaydev Vihar Bhubaneswar",
            "confidence": 0.9
        }
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = [
                {
                    "display_name": "Jaydev Vihar, Bhubaneswar, Khordha, Odisha, India",
                    "latitude": 20.2985,
                    "longitude": 85.8260,
                    "confidence": 0.88,
                    "source": "Nominatim"
                }
            ]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/ai/extract-location", json={"text": "Garbage is piling up near Jaydev Vihar"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["clues"]["village_locality"] == "Jaydev Vihar"
            assert data["candidates"][0]["latitude"] == 20.2985

@pytest.mark.asyncio
async def test_edge_case_3_road_location_description():
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": "Unit 1",
            "ward": None,
            "road_street": None,
            "landmark": "Unit 1 Market",
            "city_district": "Bhubaneswar",
            "raw_query": "Unit 1 Market Bhubaneswar",
            "confidence": 0.92
        }
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = [
                {
                    "display_name": "Unit 1 Market, Bapuji Nagar, Bhubaneswar, Odisha",
                    "latitude": 20.2642,
                    "longitude": 85.8340,
                    "confidence": 0.91,
                    "source": "Nominatim"
                }
            ]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/ai/extract-location", json={"text": "The streetlight is not working near Unit 1 Market Bhubaneswar"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["candidates"][0]["display_name"] == "Unit 1 Market, Bapuji Nagar, Bhubaneswar, Odisha"

@pytest.mark.asyncio
async def test_edge_case_4_multilingual_input():
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": "Master Canteen",
            "ward": None,
            "road_street": None,
            "landmark": "Station",
            "city_district": "Bhubaneswar",
            "raw_query": "Master Canteen Bhubaneswar",
            "confidence": 0.88
        }
        mock_get_llm.return_value = mock_llm

        with patch("app.gis.geocoder.geocoder.geocode_with_clues", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = [
                {
                    "display_name": "Master Canteen Chowk, Bhubaneswar, Odisha",
                    "latitude": 20.2680,
                    "longitude": 85.8390,
                    "confidence": 0.87,
                    "source": "Nominatim"
                }
            ]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/ai/extract-location", json={"text": "मास्टर कैंटीन के पास पानी बह रहा है भुवनेश्वर में"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["candidates"][0]["latitude"] == 20.2680

@pytest.mark.asyncio
async def test_edge_case_6_no_identifiable_location():
    with patch("app.llm.factory.get_llm_provider") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.extract_location_clues.return_value = {
            "village_locality": None,
            "ward": None,
            "road_street": "road",
            "landmark": None,
            "city_district": None,
            "raw_query": "",
            "confidence": 0.0
        }
        mock_get_llm.return_value = mock_llm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/ai/extract-location", json={"text": "There is a pothole on the road"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["clues"]["confidence"] == 0.0
        assert data["candidates"] == []


@pytest.mark.asyncio
async def test_geocoder_direct_clues_resolution_iter_main_gate():
    from app.gis.geocoder import geocoder
    from app.schemas import LocationClues
    from unittest.mock import patch, MagicMock

    clues = LocationClues(
        landmark="ITER Main Gate",
        village_locality="Jagamara",
        city_district="Bhubaneswar",
        raw_query="ITER Main Gate Bhubaneswar",
        confidence=0.9
    )

    with patch("app.gis.geocoder.requests.get") as mock_get:
        # Mock returning a candidate ONLY for the 'ITER, Jagamara, Bhubaneswar' variant
        def side_effect(*args, **kwargs):
            query = kwargs.get('params', {}).get('q', '')
            resp = MagicMock()
            if 'ITER, Jagamara' in query or 'ITER, Bhubaneswar' in query:
                resp.json.return_value = [
                    {
                        "display_name": "ITER, Bhubaneswar, Odisha, India",
                        "lat": "20.250",
                        "lon": "85.800",
                        "importance": 0.5
                    }
                ]
            else:
                resp.json.return_value = []
            return resp
        mock_get.side_effect = side_effect

        candidates = await geocoder.geocode_with_clues(clues, "waterlogging near ITER Main Gate Bhubaneswar")

        assert len(candidates) > 0
        assert candidates[0].latitude == 20.250
        assert candidates[0].display_name == "ITER, Bhubaneswar, Odisha, India"

        # Verify it constructed and tried multiple variants
        called_queries = [call.kwargs.get("params", {}).get("q") for call in mock_get.call_args_list]
        assert "ITER Main Gate, Jagamara, Bhubaneswar, Odisha, India" in called_queries
        assert "ITER, Jagamara, Bhubaneswar, Odisha, India" in called_queries
