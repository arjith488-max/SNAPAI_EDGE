"""
SnapAI Edge - Failure Tests
Tests error handling, invalid credentials, timeouts, missing models, and fallback rules.
"""

import pytest
import sys
import httpx
from pathlib import Path
from unittest.mock import AsyncMock, patch

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ai.manager import ai_manager
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.types import ProviderType, UnifiedResponse


@pytest.mark.asyncio
async def test_ollama_not_running_failure():
    provider = OllamaProvider()
    with patch.object(provider, "get_installed_models", new_callable=AsyncMock) as mock_installed:
        mock_installed.return_value = []
        provider._is_running = False

        resp = await provider.generate([{"role": "user", "content": "Hello"}])
        assert isinstance(resp, UnifiedResponse)
        assert "not running" in resp.response.lower()
        assert resp.metadata.get("error") == "ollama_not_running"


@pytest.mark.asyncio
async def test_unavailable_model_in_ollama():
    provider = OllamaProvider()
    with patch.object(provider, "get_installed_models", new_callable=AsyncMock) as mock_installed:
        mock_installed.return_value = ["llama3.2"]
        provider._is_running = True

        resp = await provider.generate(
            [{"role": "user", "content": "Hello"}],
            model="non-existent-model-xyz",
        )
        assert isinstance(resp, UnifiedResponse)
        assert "not installed" in resp.response.lower()
        assert resp.metadata.get("error") == "model_not_installed"


@pytest.mark.asyncio
async def test_explicit_provider_failure_does_not_silently_switch():
    """
    Section 20:
    If the user selects OpenAI and OpenAI fails, show:
    'OpenAI request failed. [Retry] [Switch to Auto]'
    Never silently switch when explicit provider is selected.
    """
    # Mock openai provider to fail
    with patch.object(
        ai_manager.get_provider(ProviderType.OPENAI.value),
        "generate",
        new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = UnifiedResponse(
            provider="openai",
            model="gpt-4o-mini",
            mode="cloud",
            response="Authentication failed",
            latency_ms=100.0,
            metadata={"error": "authentication_error", "details": "Invalid API key"},
        )

        resp = await ai_manager.generate(
            messages=[{"role": "user", "content": "Hello"}],
            provider="openai",  # Explicit provider
        )

        assert resp.provider == "openai"
        assert "request failed" in resp.response
        assert "[Retry]" in resp.response
        assert "[Switch to Auto]" in resp.response


@pytest.mark.asyncio
async def test_auto_mode_safely_falls_back():
    """
    In AUTO mode, if chosen provider fails, can safely fallback.
    """
    # Primary chosen fails, fallback succeeds
    gemini_p = ai_manager.get_provider(ProviderType.GEMINI.value)
    local_p = ai_manager.get_provider(ProviderType.LOCAL.value)

    with patch.object(gemini_p, "generate", new_callable=AsyncMock) as mock_gemini, \
         patch.object(local_p, "generate", new_callable=AsyncMock) as mock_local:

        mock_gemini.return_value = UnifiedResponse(
            provider="gemini",
            model="gemini-1.5-flash",
            mode="cloud",
            response="Quota exceeded",
            latency_ms=50.0,
            metadata={"error": "quota_exceeded"},
        )
        mock_local.return_value = UnifiedResponse(
            provider="local",
            model="local:snapdragon-npu",
            mode="local",
            response="Safe local response",
            latency_ms=10.0,
            metadata={},
        )

        resp = await ai_manager.generate(
            messages=[{"role": "user", "content": "Hello"}],
            provider="auto",
        )
        # In auto mode, must not crash and return a valid UnifiedResponse
        assert isinstance(resp, UnifiedResponse)


@pytest.mark.asyncio
async def test_network_timeout_handling():
    provider = OllamaProvider()
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")), \
         patch.object(provider, "get_installed_models", new_callable=AsyncMock) as mock_installed:
        mock_installed.return_value = ["llama3.2"]
        provider._is_running = True

        resp = await provider.generate([{"role": "user", "content": "Hello"}])
        assert "error" in resp.metadata
        assert "timed out" in resp.response.lower()
