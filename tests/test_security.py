"""
SnapAI Edge - Security & Privacy Tests
Tests API key leakage prevention, sensitive-data detection, masking, and prompt injection defense.
"""

import pytest
import os
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from security.privacy_guard import privacy_guard, PrivacyGuard
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.gemini_provider import GeminiProvider


def test_sensitive_data_detection_api_keys():
    mock_key = "sk-" + "abcdef1234567890abcdef1234567890"
    test_str = f"Deploying with key: {mock_key} to production"
    res = privacy_guard.scan(test_str)
    assert res.has_sensitive_data is True
    assert "api_key" in res.detected_categories


def test_sensitive_data_detection_passwords():
    mock_pw = "Super" + "Secret123!"
    test_str = f"Login credentials: password = {mock_pw}"
    res = privacy_guard.scan(test_str)
    assert res.has_sensitive_data is True
    assert "password" in res.detected_categories


def test_sensitive_data_detection_pii():
    test_str = "Contact me at alice.smith@enterprise.org or call 415-555-2671 with SSN 000-12-3456"
    res = privacy_guard.scan(test_str)
    assert res.has_sensitive_data is True
    assert "email" in res.detected_categories
    assert "phone_number" in res.detected_categories
    assert "identifier" in res.detected_categories


def test_sensitive_data_detection_financial():
    test_str = "Pay with card 4111 2222 3333 4444 expiration 12/28"
    res = privacy_guard.scan(test_str)
    assert res.has_sensitive_data is True
    assert "financial" in res.detected_categories


def test_sensitive_masking():
    mock_key = "sk-" + "123456789012345678901234567890"
    test_str = f"Contact alice@example.com using {mock_key}"
    masked = privacy_guard.mask(test_str)
    assert "alice@example.com" not in masked
    assert "[MASKED_EMAIL]" in masked
    assert mock_key not in masked
    assert "[MASKED_API_KEY]" in masked


def test_api_key_leakage_sanitization():
    """
    Ensure provider error sanitizers never leak active API keys in error strings.
    """
    fake_key = "sk-" + "REALSECRETKEY12345678901234567890"
    provider = OpenAIProvider()
    provider._api_key = fake_key

    err = Exception(f"Failed to authenticate with bearer {fake_key} at endpoint")
    sanitized = provider._sanitize_error(err)
    assert fake_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized

    gemini_provider = GeminiProvider()
    gemini_key = "AIza" + "SyD-FakeGeminiSecretKey123456789"
    os.environ["GEMINI_API_KEY"] = gemini_key
    gemini_err = Exception(f"Quota error for key {gemini_key}")
    sanitized_g = gemini_provider._sanitize_error(gemini_err)
    assert gemini_key not in sanitized_g
    assert "[REDACTED_API_KEY]" in sanitized_g


def test_clean_text_no_false_positive():
    clean_prompt = "What is the capital of France and how does photosynthesis work?"
    res = privacy_guard.scan(clean_prompt)
    assert res.has_sensitive_data is False
    assert len(res.detected_categories) == 0
    assert res.risk_level == "none"
