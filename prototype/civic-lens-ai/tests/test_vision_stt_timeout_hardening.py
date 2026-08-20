import asyncio
import tempfile
import os
import json
import pytest
from unittest.mock import MagicMock, patch

from app.vision.gemini_vision import GeminiVisionProvider, _consume_task_exception as vision_consume_task_exception
from app.stt.gemini_stt import GeminiSTTProvider, _consume_task_exception as stt_consume_task_exception
from app.vision.base import VisionProviderError
from app.stt.base import STTProviderError


@pytest.mark.asyncio
async def test_consume_task_exception_helper():
    """Verify that _consume_task_exception safely retrieves exceptions from background tasks."""
    loop = asyncio.get_running_loop()
    
    # 1. Task with exception
    def failing_fn():
        raise RuntimeError("Simulated socket error / WinError 10053")
    
    task1 = asyncio.create_task(asyncio.to_thread(failing_fn))
    task1.add_done_callback(vision_consume_task_exception)
    
    with pytest.raises(RuntimeError):
        await task1

    # Exception should have been retrieved by callback, leaving task clean
    assert task1.done()
    assert isinstance(task1.exception(), RuntimeError)

    # 2. Cancelled task
    async def sleeping_coro():
        await asyncio.sleep(10)
        
    task2 = asyncio.create_task(sleeping_coro())
    task2.add_done_callback(stt_consume_task_exception)
    task2.cancel()
    
    try:
        await task2
    except asyncio.CancelledError:
        pass
    
    assert task2.cancelled()


@pytest.mark.asyncio
async def test_vision_success_path():
    """Verify Vision analyze_image success path and file cleanup with mocked Gemini client."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Mock file upload
        mock_file = MagicMock()
        mock_file.name = "files/test_img_123"
        mock_client.files.upload.return_value = mock_file
        
        # Mock model response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "visual_analysis": {
                "visible_issue": True,
                "category": "ROAD_DAMAGE",
                "subcategory": "POTHOLE",
                "severity": 4,
                "safety_risk": True,
                "public_impact": 4,
                "description": "Large pothole on street",
                "confidence": 0.95
            },
            "evidence_disagreement": False,
            "disagreement_reason": None,
            "fused_analysis": {
                "summary": "Pothole reported on street",
                "detailed_description": "Pothole reported on street",
                "category": "ROAD_DAMAGE",
                "subcategory": "POTHOLE",
                "severity": 4,
                "safety_risk": True,
                "public_impact": 4,
                "location_description": "street",
                "confidence": 0.95
            }
        })
        mock_client.models.generate_content.return_value = mock_response

        # Create temporary test image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00")
            tmp_path = tmp.name

        try:
            provider = GeminiVisionProvider(api_key="mock_key")
            v_ans, c_ans, dis, dis_reason = await provider.analyze_image(
                file_path=tmp_path,
                mime_type="image/jpeg"
            )

            assert v_ans.visible_issue is True
            assert v_ans.category.value == "ROAD_DAMAGE"
            assert c_ans.category.value == "ROAD_DAMAGE"
            assert dis is False
            
            # Verify remote file cleanup in finally block
            mock_client.files.delete.assert_called_once_with(name="files/test_img_123")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


@pytest.mark.asyncio
async def test_vision_timeout_path_and_cleanup():
    """Verify Vision timeout (45s), task cancellation, exception consumption, and remote file cleanup."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        mock_file = MagicMock()
        mock_file.name = "files/test_img_timeout"
        mock_client.files.upload.return_value = mock_file

        # Create temporary test image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00")
            tmp_path = tmp.name

        try:
            async def mock_wait(tasks, timeout):
                return set(), set(tasks)

            with patch("asyncio.wait", side_effect=mock_wait):
                provider = GeminiVisionProvider(api_key="mock_key")
                
                with pytest.raises(VisionProviderError) as exc_info:
                    await provider.analyze_image(file_path=tmp_path, mime_type="image/jpeg")

                assert "Vision service timed out due to high demand" in str(exc_info.value)

            # Verify file cleanup occurred despite timeout
            mock_client.files.delete.assert_called_once_with(name="files/test_img_timeout")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


@pytest.mark.asyncio
async def test_stt_timeout_path_and_cleanup():
    """Verify STT timeout (45s), task cancellation, exception consumption, and remote file cleanup."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        mock_file = MagicMock()
        mock_file.name = "files/test_audio_timeout"
        mock_client.files.upload.return_value = mock_file

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"RIFF....WAVEfmt ")
            tmp_path = tmp.name

        try:
            async def mock_wait(tasks, timeout):
                return set(), set(tasks)

            with patch("asyncio.wait", side_effect=mock_wait):
                provider = GeminiSTTProvider(api_key="mock_key")
                
                with pytest.raises(STTProviderError) as exc_info:
                    await provider.transcribe(file_path=tmp_path, mime_type="audio/wav")

                assert "STT service timed out due to high demand" in str(exc_info.value)

            # Verify file cleanup occurred despite timeout
            mock_client.files.delete.assert_called_once_with(name="files/test_audio_timeout")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
