"""
SnapAI Edge - AI Router Tests
Tests all routing decisions, modes, privacy enforcement, and fallback behavior.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ai.router import AIRouter, RoutingDecision
from ai.types import ProviderType, UserMode


@pytest.mark.asyncio
async def test_offline_mode_prohibits_cloud():
    router = AIRouter()
    messages = [{"role": "user", "content": "Explain edge AI"}]
    # Force user mode to OFFLINE ONLY
    decision = await router.route(messages=messages, user_mode=UserMode.OFFLINE_ONLY.value)

    assert isinstance(decision, RoutingDecision)
    assert decision.mode in ("offline", "local")
    assert decision.provider in (ProviderType.OLLAMA.value, ProviderType.LOCAL.value)
    # Must never select OpenAI or Gemini in offline mode
    assert decision.provider != ProviderType.OPENAI.value
    assert decision.provider != ProviderType.GEMINI.value


@pytest.mark.asyncio
async def test_network_offline_forces_local():
    router = AIRouter()
    messages = [{"role": "user", "content": "Explain machine learning"}]

    # Mock is_online to return False
    with patch.object(router, "is_online", new_callable=AsyncMock) as mock_online:
        mock_online.return_value = False
        decision = await router.route(messages=messages, user_mode=UserMode.AUTO.value)

        assert decision.mode in ("offline", "local")
        assert decision.provider != ProviderType.OPENAI.value
        assert decision.provider != ProviderType.GEMINI.value


@pytest.mark.asyncio
async def test_privacy_mode_sensitive_data_forces_local():
    router = AIRouter()
    # Prompt containing sensitive password / API key pattern
    mock_token = "sk-" + "123456789012345678901234567890"
    sensitive_prompt = f"Here is my secret access token: {mock_token} and my password is Password123!"
    messages = [{"role": "user", "content": sensitive_prompt}]

    decision = await router.route(
        messages=messages,
        user_mode=UserMode.AUTO.value,
        allow_cloud_override=False,
    )

    # Privacy guard must trigger local routing
    assert decision.provider in (ProviderType.OLLAMA.value, ProviderType.LOCAL.value)
    assert decision.privacy_warning is not None
    assert any("privacy" in r.lower() or "sensitive" in r.lower() for r in decision.reasons)


@pytest.mark.asyncio
async def test_explicit_provider_selection():
    router = AIRouter()
    messages = [{"role": "user", "content": "Hello"}]

    # Explicit OpenAI
    dec_openai = await router.route(messages=messages, requested_provider="openai")
    assert dec_openai.provider == ProviderType.OPENAI.value
    assert dec_openai.mode == "cloud"

    # Explicit Gemini
    dec_gemini = await router.route(messages=messages, requested_provider="gemini")
    assert dec_gemini.provider == ProviderType.GEMINI.value
    assert dec_gemini.mode == "cloud"

    # Explicit Ollama
    dec_ollama = await router.route(messages=messages, requested_provider="ollama")
    assert dec_ollama.provider == ProviderType.OLLAMA.value


@pytest.mark.asyncio
async def test_local_first_mode():
    router = AIRouter()
    messages = [{"role": "user", "content": "Write a short poem"}]

    # When Ollama is mocked as available
    with patch.object(router, "is_ollama_available", new_callable=AsyncMock) as mock_ollama, \
         patch.object(router, "get_installed_ollama_models", new_callable=AsyncMock) as mock_models:
        mock_ollama.return_value = True
        mock_models.return_value = ["llama3.2"]

        decision = await router.route(messages=messages, user_mode=UserMode.LOCAL_FIRST.value)
        assert decision.provider == ProviderType.OLLAMA.value
        assert decision.mode == "local"
        assert decision.model == "llama3.2"


@pytest.mark.asyncio
async def test_auto_provider_routing_reasons():
    router = AIRouter()
    messages = [{"role": "user", "content": "Explain quantum computing"}]
    decision = await router.route(messages=messages, user_mode=UserMode.AUTO.value)

    assert len(decision.reasons) > 0
    reason_str = decision.to_reason_string()
    assert "Selected because:" in reason_str
