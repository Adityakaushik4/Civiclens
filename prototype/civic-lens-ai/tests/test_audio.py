import io
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import TranscriptionResult, Category, ConfidenceStatus
from app.stt.base import SpeechToTextProvider, STTProviderError, STTInvalidAudioError
from app.llm.base import LLMProviderError
from tests.test_analysis import MockLLMProvider

client = TestClient(app)


def generate_synthetic_wav_bytes(size_bytes: int = 128) -> bytes:
    """Generate a minimal valid RIFF WAV header + dummy PCM audio payload."""
    # 44-byte standard RIFF WAV header
    header = bytearray(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    if size_bytes > len(header):
        padding = b"\x00" * (size_bytes - len(header))
        return bytes(header + padding)
    return bytes(header[:size_bytes])


class MockSTTProvider(SpeechToTextProvider):
    def __init__(self, text="There is a huge pothole near the school.", language="en", raise_error=None):
        self.text = text
        self.language = language
        self.raise_error = raise_error

    async def transcribe(self, file_path: str, mime_type: str) -> TranscriptionResult:
        if self.raise_error:
            raise self.raise_error
        return TranscriptionResult(
            text=self.text,
            language=self.language,
            confidence=0.95,
            provider="mock_stt"
        )


def test_invalid_file_extension():
    files = {"file": ("test.txt", b"plain text data", "text/plain")}
    response = client.post("/api/v1/ai/analyze-audio", files=files)
    assert response.status_code == 415
    assert "Unsupported Audio Format" in response.json()["error"]


def test_empty_audio_file():
    files = {"file": ("empty.wav", b"", "audio/wav")}
    response = client.post("/api/v1/ai/analyze-audio", files=files)
    assert response.status_code == 400
    assert "Empty Audio File" in response.json()["error"]


def test_oversized_audio_file():
    # 11 MB payload (exceeding default 10MB limit)
    large_payload = b"\x00" * (11 * 1024 * 1024)
    files = {"file": ("huge.wav", large_payload, "audio/wav")}
    response = client.post("/api/v1/ai/analyze-audio", files=files)
    assert response.status_code == 413
    assert "Oversized Audio File" in response.json()["error"]


def test_stt_provider_failure():
    wav_data = generate_synthetic_wav_bytes(256)
    files = {"file": ("complaint.wav", wav_data, "audio/wav")}
    
    with patch("app.main.get_stt_provider") as mock_stt_factory:
        mock_stt_factory.return_value = MockSTTProvider(raise_error=STTProviderError("STT API Offline"))
        response = client.post("/api/v1/ai/analyze-audio", files=files)
        assert response.status_code == 503
        assert response.json()["error"] == "STT Provider Error"


def test_downstream_llm_failure():
    wav_data = generate_synthetic_wav_bytes(256)
    files = {"file": ("complaint.wav", wav_data, "audio/wav")}

    with patch("app.main.get_stt_provider") as mock_stt_factory, \
         patch("app.pipeline.get_llm_provider") as mock_llm_factory:
        mock_stt_factory.return_value = MockSTTProvider(text="Pothole near school")
        mock_llm_factory.return_value = MockLLMProvider(raise_error=LLMProviderError("LLM API Timeout"))

        response = client.post("/api/v1/ai/analyze-audio", files=files)
        assert response.status_code == 503
        assert response.json()["error"] == "LLM Provider Error"


def test_audio_english_end_to_end():
    wav_data = generate_synthetic_wav_bytes(256)
    files = {"file": ("english_pothole.wav", wav_data, "audio/wav")}

    mock_llm_output = {
        "category": "ROAD_DAMAGE",
        "subcategory": "POTHOLE",
        "severity": 4,
        "safety_risk": True,
        "public_impact": 4,
        "location_description": "near the school",
        "summary": "Pothole near school",
        "confidence": 0.95
    }

    with patch("app.main.get_stt_provider") as mock_stt_factory, \
         patch("app.pipeline.get_llm_provider") as mock_llm_factory:
        mock_stt_factory.return_value = MockSTTProvider(text="There is a huge pothole near the school.", language="en")
        mock_llm_factory.return_value = MockLLMProvider(return_data=mock_llm_output)

        response = client.post("/api/v1/ai/analyze-audio", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["input_type"] == "audio"
        assert res["transcription"]["text"] == "There is a huge pothole near the school."
        assert res["transcription"]["language"] == "en"
        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["analysis"]["subcategory"] == "POTHOLE"
        assert res["analysis"]["severity"] == 4
        assert res["analysis"]["confidence_status"] == "ACCEPTED"


def test_audio_hindi_end_to_end():
    wav_data = generate_synthetic_wav_bytes(256)
    files = {"file": ("hindi_pothole.wav", wav_data, "audio/wav")}

    mock_llm_output = {
        "category": "ROAD_DAMAGE",
        "subcategory": "POTHOLE",
        "severity": 4,
        "safety_risk": True,
        "public_impact": 4,
        "location_description": "स्कूल के पास",
        "summary": "Pothole near school in Hindi",
        "confidence": 0.94
    }

    with patch("app.main.get_stt_provider") as mock_stt_factory, \
         patch("app.pipeline.get_llm_provider") as mock_llm_factory:
        mock_stt_factory.return_value = MockSTTProvider(text="स्कूल के पास सड़क पर बहुत बड़ा गड्ढा है।", language="hi")
        mock_llm_factory.return_value = MockLLMProvider(return_data=mock_llm_output)

        response = client.post("/api/v1/ai/analyze-audio", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["input_type"] == "audio"
        assert res["transcription"]["text"] == "स्कूल के पास सड़क पर बहुत बड़ा गड्ढा है।"
        assert res["transcription"]["language"] == "hi"
        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["analysis"]["subcategory"] == "POTHOLE"


def test_audio_odia_end_to_end():
    wav_data = generate_synthetic_wav_bytes(256)
    files = {"file": ("odia_pothole.wav", wav_data, "audio/wav")}

    mock_llm_output = {
        "category": "ROAD_DAMAGE",
        "subcategory": "POTHOLE",
        "severity": 4,
        "safety_risk": True,
        "public_impact": 4,
        "location_description": "ସ୍କୁଲ ପାଖରେ",
        "summary": "Pothole near school in Odia",
        "confidence": 0.92
    }

    with patch("app.main.get_stt_provider") as mock_stt_factory, \
         patch("app.pipeline.get_llm_provider") as mock_llm_factory:
        mock_stt_factory.return_value = MockSTTProvider(text="ସ୍କୁଲ ପାଖରେ ରାସ୍ତାରେ ବଡ଼ ଗାତ ଅଛି।", language="or")
        mock_llm_factory.return_value = MockLLMProvider(return_data=mock_llm_output)

        response = client.post("/api/v1/ai/analyze-audio", files=files)
        assert response.status_code == 200
        res = response.json()

        assert res["input_type"] == "audio"
        assert res["transcription"]["text"] == "ସ୍କୁଲ ପାଖରେ ରାସ୍ତାରେ ବଡ଼ ଗାତ ଅଛି।"
        assert res["transcription"]["language"] == "or"
        assert res["analysis"]["category"] == "ROAD_DAMAGE"
        assert res["analysis"]["subcategory"] == "POTHOLE"
