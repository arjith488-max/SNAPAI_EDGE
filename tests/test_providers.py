"""
SnapAI Edge - Provider Tests
Tests for OpenAI, Gemini, Ollama, and Snapdragon/Local Providers.
"""

import pytest
import os
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ai.types import ProviderType, HardwareStatus, UnifiedResponse, ProviderStatus
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.local_provider import LocalProvider


@pytest.mark.asyncio
async def test_openai_provider_initialization():
    provider = OpenAIProvider()
    assert provider.provider_id == ProviderType.OPENAI.value
    assert provider.provider_name == "OpenAI"
    assert provider.is_local is False
    caps = provider.get_capabilities()
    assert "text" in caps
    assert "vision" in caps


@pytest.mark.asyncio
async def test_openai_unconfigured_graceful_handling():
    # Force unconfigured
    orig_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["OPENAI_API_KEY"] = ""
        provider = OpenAIProvider()
        status = await provider.health_check()
        assert status.available is False
        assert status.configured is False

        resp = await provider.generate([{"role": "user", "content": "Hello"}])
        assert isinstance(resp, UnifiedResponse)
        assert resp.mode == "cloud"
        assert "not configured" in resp.response.lower()
        assert resp.network_used is False
    finally:
        if orig_key is not None:
            os.environ["OPENAI_API_KEY"] = orig_key


@pytest.mark.asyncio
async def test_gemini_provider_initialization():
    provider = GeminiProvider()
    assert provider.provider_id == ProviderType.GEMINI.value
    assert provider.provider_name == "Google Gemini"
    assert provider.is_local is False
    caps = provider.get_capabilities()
    assert "text" in caps
    assert "vision" in caps


@pytest.mark.asyncio
async def test_gemini_unconfigured_graceful_handling():
    orig_key = os.environ.get("GEMINI_API_KEY")
    orig_gkey = os.environ.get("GOOGLE_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = ""
        os.environ["GOOGLE_API_KEY"] = ""
        provider = GeminiProvider()
        status = await provider.health_check()
        assert status.available is False

        resp = await provider.generate([{"role": "user", "content": "Hello"}])
        assert isinstance(resp, UnifiedResponse)
        assert resp.mode == "cloud"
        assert "not configured" in resp.response.lower()
    finally:
        if orig_key is not None:
            os.environ["GEMINI_API_KEY"] = orig_key
        if orig_gkey is not None:
            os.environ["GOOGLE_API_KEY"] = orig_gkey


@pytest.mark.asyncio
async def test_ollama_provider_detection():
    provider = OllamaProvider()
    assert provider.provider_id == ProviderType.OLLAMA.value
    assert provider.is_local is True
    status = await provider.health_check()
    assert isinstance(status, ProviderStatus)
    assert status.type == "local"
    # When Ollama is not running, must gracefully report not running
    if not status.available:
        assert "unreachable" in status.status_text.lower() or "not running" in status.status_text.lower()


@pytest.mark.asyncio
async def test_local_provider_hardware_detection():
    provider = LocalProvider()
    assert provider.provider_id == ProviderType.LOCAL.value
    assert provider.is_local is True

    hw = provider.detect_hardware()
    assert "cpu_brand" in hw
    assert "architecture" in hw
    assert "is_snapdragon" in hw
    assert "snapdragon_status" in hw
    assert hw["snapdragon_status"] in (
        HardwareStatus.AVAILABLE.value,
        HardwareStatus.UNAVAILABLE.value,
        HardwareStatus.UNKNOWN.value,
    )

    # Must generate a valid local response
    resp = await provider.generate([{"role": "user", "content": "Test hardware"}])
    assert isinstance(resp, UnifiedResponse)
    assert resp.mode == "local"
    assert resp.local_processing is True
    assert resp.network_used is False
