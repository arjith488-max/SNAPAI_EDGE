"""
SnapAI Edge - API Endpoint Integration Tests
Tests all endpoints from Section 18: /chat, /stream, /providers, /models, /route, /health, /provider/test, /status.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database.db import init_db
init_db()

import main

client = TestClient(main.app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "SnapAI Edge"


def test_get_providers_endpoint():
    res = client.get("/api/ai/providers")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    provider_ids = [p["provider"] for p in data["providers"]]
    assert "openai" in provider_ids
    assert "gemini" in provider_ids
    assert "ollama" in provider_ids
    assert "local" in provider_ids


def test_get_models_endpoint():
    res = client.get("/api/ai/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) >= 4
    for m in data["models"]:
        assert "id" in m
        assert "provider" in m
        assert "capabilities" in m
        assert "location" in m


def test_route_simulation_endpoint():
    res = client.post(
        "/api/ai/route",
        json={"message": "Write a Python script to sort a list", "mode": "auto"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "model" in data
    assert "mode" in data
    assert "reasons" in data
    assert len(data["reasons"]) > 0


def test_providers_health_endpoint():
    res = client.post("/api/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "providers" in data


def test_system_status_endpoint():
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "online" in data
    assert "active_mode" in data
    assert "hardware" in data
    assert "is_snapdragon" in data["hardware"]


def test_privacy_scan_endpoint():
    mock_key = "sk-" + "123456789012345678901234567890"
    res = client.post(
        "/api/ai/privacy/scan",
        json={"text": f"My email is test@company.com and secret key is {mock_key}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_sensitive_data"] is True
    assert "api_key" in data["detected_categories"]
    assert "email" in data["detected_categories"]
    assert "[MASKED_API_KEY]" in data["masked_preview"]


def test_unified_chat_endpoint_structure():
    res = client.post(
        "/api/ai/chat",
        json={
            "message": "Hello SnapAI",
            "provider": "local",
            "mode": "local",
        },
    )
    assert res.status_code == 200
    data = res.json()
    # Must contain unified response attributes (Section 9 & 18)
    assert "provider" in data
    assert "model" in data
    assert "mode" in data
    assert "latency_ms" in data
    assert "response" in data or "content" in data


def test_streaming_endpoint():
    res = client.post(
        "/api/ai/stream",
        json={
            "message": "Hello",
            "provider": "local",
            "mode": "local",
        },
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    content = res.text
    assert "data:" in content
    assert '"done": true' in content
