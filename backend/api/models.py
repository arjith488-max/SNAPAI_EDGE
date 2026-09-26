"""SnapAI Edge - Model Manager API"""

import os
from fastapi import APIRouter

router = APIRouter()

# Catalog of supported models with their metadata
MODEL_CATALOG = [
    {
        "id": "jina-embeddings-v3",
        "name": "Jina Embeddings v3",
        "type": "embedding",
        "size_mb": None,
        "source": "Jina AI Cloud",
        "runtime": "cloud_api",
        "status": "ready" if os.getenv("JINA_API_KEY") else "api_key_required",
        "local": False,
        "provider": "Jina AI",
        "task": "Text embeddings for RAG",
        "license": "Apache 2.0 (API)",
        "quantization": "N/A",
        "latency_note": "Cloud API - requires internet",
    },
    {
        "id": "jina-reranker-v2",
        "name": "Jina Reranker v2",
        "type": "reranker",
        "size_mb": None,
        "source": "Jina AI Cloud",
        "runtime": "cloud_api",
        "status": "ready" if os.getenv("JINA_API_KEY") else "api_key_required",
        "local": False,
        "provider": "Jina AI",
        "task": "Document reranking for RAG",
        "license": "Apache 2.0 (API)",
        "latency_note": "Cloud API",
    },
    {
        "id": "llava",
        "name": "LLaVA (Vision)",
        "type": "vision_llm",
        "size_mb": 4700,
        "source": "Ollama",
        "runtime": "ollama_local",
        "status": "download_required",
        "local": True,
        "provider": "Meta (via Ollama)",
        "task": "Image understanding, VQA, OCR",
        "license": "LLaMA 2 Community License",
        "quantization": "Q4_K_M",
        "install_cmd": "ollama pull llava",
    },
    {
        "id": "llama3.2",
        "name": "Llama 3.2 (3B)",
        "type": "llm",
        "size_mb": 2000,
        "source": "Ollama",
        "runtime": "ollama_local",
        "status": "download_required",
        "local": True,
        "provider": "Meta (via Ollama)",
        "task": "Text generation, chat",
        "license": "LLaMA 3.2 Community License",
        "quantization": "Q4_K_M",
        "install_cmd": "ollama pull llama3.2",
    },
    {
        "id": "whisper-tiny",
        "name": "Whisper Tiny",
        "type": "speech",
        "size_mb": 75,
        "source": "OpenAI (via faster-whisper)",
        "runtime": "faster_whisper_local",
        "status": "install_required",
        "local": True,
        "provider": "OpenAI (open-source weights)",
        "task": "Speech recognition (ASR)",
        "license": "MIT",
        "quantization": "int8",
        "install_cmd": "pip install faster-whisper",
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "type": "llm",
        "size_mb": None,
        "source": "OpenAI Cloud",
        "runtime": "openai_api",
        "status": "ready" if os.getenv("OPENAI_API_KEY") else "api_key_required",
        "local": False,
        "provider": "OpenAI",
        "task": "Chat, vision, code, documents",
        "license": "Commercial API",
        "latency_note": "Cloud API",
    },
    {
        "id": "qai-clip-vit-b32",
        "name": "CLIP ViT-B/32 (Qualcomm AI Hub)",
        "type": "vision_embedding",
        "size_mb": 170,
        "source": "Qualcomm AI Hub",
        "runtime": "onnx_qnn",
        "status": "planned",
        "local": True,
        "provider": "Qualcomm AI Hub",
        "task": "Image-text matching, visual search",
        "license": "See Qualcomm AI Hub license",
        "quantization": "INT8 (QNN)",
        "latency_note": "Requires Qualcomm QNN runtime",
        "snapdragon_optimized": True,
        "hub_url": "https://aihub.qualcomm.com/models/clip_vit_b32",
    },
    {
        "id": "qai-whisper-base",
        "name": "Whisper Base (Qualcomm AI Hub)",
        "type": "speech",
        "size_mb": 145,
        "source": "Qualcomm AI Hub",
        "runtime": "onnx_qnn",
        "status": "planned",
        "local": True,
        "provider": "Qualcomm AI Hub",
        "task": "Local speech recognition on NPU",
        "license": "See Qualcomm AI Hub license",
        "quantization": "INT8 (QNN)",
        "snapdragon_optimized": True,
        "hub_url": "https://aihub.qualcomm.com/models/whisper_base_en",
    },
]


@router.get("")
async def list_models():
    """Return model catalog with live status checks."""
    # Check Ollama availability
    ollama_models = set()
    try:
        import httpx
        r = httpx.get(f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags", timeout=3)
        if r.status_code == 200:
            for m in r.json().get("models", []):
                ollama_models.add(m.get("name", "").split(":")[0])
    except Exception:
        pass

    catalog = []
    for m in MODEL_CATALOG:
        entry = dict(m)
        # Update live Ollama status
        if m["runtime"] == "ollama_local":
            entry["status"] = "ready" if m["id"] in ollama_models else "download_required"
            entry["ollama_installed"] = m["id"] in ollama_models
        catalog.append(entry)

    return {
        "models": catalog,
        "ollama_running": len(ollama_models) > 0,
        "jina_configured": bool(os.getenv("JINA_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@router.get("/{model_id}")
async def get_model(model_id: str):
    for m in MODEL_CATALOG:
        if m["id"] == model_id:
            return m
    return {"error": "Model not found"}
