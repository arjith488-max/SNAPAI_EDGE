"""
SnapAI Edge - Unified AI API Endpoints
Implements:
- POST /api/ai/chat
- POST /api/ai/stream
- GET /api/ai/providers
- GET /api/ai/models
- POST /api/ai/route
- POST /api/ai/health
- POST /api/ai/provider/test
- GET /api/ai/status
- POST /api/ai/privacy/scan
"""

import uuid
import json
import asyncio
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db, Conversation, Message
from ai.manager import ai_manager
from ai.router import router as ai_router
from ai.models.registry import model_registry
from ai.providers.local_provider import LocalProvider
from ai.types import ProviderType, UserMode, UnifiedResponse, ModelInfo, ProviderStatus
from security.privacy_guard import privacy_guard

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = "user"
    content: str
    attachments: Optional[List[Any]] = None


class UnifiedChatRequest(BaseModel):
    messages: Optional[List[ChatMessage]] = None
    message: Optional[str] = None  # Single message convenience
    provider: str = "auto"         # "auto" | "openai" | "gemini" | "ollama" | "local"
    mode: str = UserMode.AUTO.value  # "auto" | "local_first" | "cloud_first" | "hybrid" | "offline_only"
    model: Optional[str] = None
    conversation_id: Optional[str] = None
    prefer_local: bool = False
    allow_cloud_override: bool = False
    attachments: Optional[List[Any]] = None


class RouteRequest(BaseModel):
    messages: Optional[List[ChatMessage]] = None
    message: Optional[str] = None
    provider: str = "auto"
    mode: str = UserMode.AUTO.value
    model: Optional[str] = None
    attachments: Optional[List[Any]] = None
    allow_cloud_override: bool = False


class ProviderTestRequest(BaseModel):
    provider: str
    prompt: Optional[str] = "Hello from SnapAI Edge"


class PrivacyScanRequest(BaseModel):
    text: str


def _normalize_messages(req: Union[UnifiedChatRequest, RouteRequest]) -> List[Dict[str, Any]]:
    if req.messages:
        return [m.model_dump() for m in req.messages]
    elif req.message:
        return [{"role": "user", "content": req.message, "attachments": req.attachments or []}]
    return [{"role": "user", "content": "Hello"}]


# ─── 1. Unified Chat Endpoint ──────────────────────────────────
@router.post("/chat")
async def unified_chat(req: UnifiedChatRequest, db: Session = Depends(get_db)):
    """
    Standard generation endpoint returning normalized UnifiedResponse format.
    Persists to SQLite history if conversation_id provided or generated.
    """
    messages = _normalize_messages(req)
    last_user_text = messages[-1].get("content", "")

    # Mode mapping
    effective_mode = req.mode
    if req.prefer_local and effective_mode == UserMode.AUTO.value:
        effective_mode = UserMode.LOCAL_FIRST.value

    # Conversation management
    conv_id = req.conversation_id or str(uuid.uuid4())
    conv = db.query(Conversation).filter_by(id=conv_id).first()
    if not conv:
        conv = Conversation(id=conv_id, title=str(last_user_text)[:60] or "New Conversation")
        db.add(conv)
        db.commit()

    # Prepend conversation history if not already provided in messages
    if len(messages) <= 1:
        history = (
            db.query(Message)
            .filter_by(conversation_id=conv_id)
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )
        history_msgs = [{"role": m.role, "content": m.content} for m in reversed(history)]
        system_msg = {
            "role": "system",
            "content": (
                "You are SnapAI Edge, a private multimodal AI assistant optimized for Snapdragon-powered PCs. "
                "Be concise, accurate, and helpful. Never fabricate benchmarks or hardware capabilities."
            ),
        }
        messages = [system_msg] + history_msgs + messages

    # Execute generation via AI Model Manager
    result: UnifiedResponse = await ai_manager.generate(
        messages=messages,
        provider=req.provider,
        mode=effective_mode,
        model=req.model,
        attachments=req.attachments,
        allow_cloud_override=req.allow_cloud_override,
    )

    # Persist user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=str(last_user_text),
        attachments=json.dumps(req.attachments) if req.attachments else None,
    )
    db.add(user_msg)

    # Persist assistant response
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="assistant",
        content=result.response,
        mode=result.mode,
        model=result.model,
        latency_ms=result.latency_ms,
    )
    db.add(assistant_msg)

    if conv.title == "New Conversation" and last_user_text:
        conv.title = str(last_user_text)[:60]
    db.commit()

    # Return response complying with Section 9 & 18
    resp_dict = result.model_dump()
    resp_dict["conversation_id"] = conv_id
    resp_dict["message_id"] = assistant_msg.id
    # Ensure backward compatibility aliases for existing frontend Chat
    resp_dict["content"] = result.response
    resp_dict["processed_locally"] = result.local_processing
    return resp_dict


# ─── 2. Streaming Chat Endpoint ────────────────────────────────
@router.post("/stream")
async def unified_stream(req: UnifiedChatRequest):
    """
    Streaming generation endpoint returning Server-Sent Events (SSE).
    """
    messages = _normalize_messages(req)
    effective_mode = req.mode
    if req.prefer_local and effective_mode == UserMode.AUTO.value:
        effective_mode = UserMode.LOCAL_FIRST.value

    async def event_generator():
        try:
            async for token in ai_manager.stream(
                messages=messages,
                provider=req.provider,
                mode=effective_mode,
                model=req.model,
                attachments=req.attachments,
                allow_cloud_override=req.allow_cloud_override,
            ):
                payload = json.dumps({"token": token, "done": False})
                yield f"data: {payload}\n\n"
            
            # Send completion signal
            end_payload = json.dumps({"token": "", "done": True})
            yield f"data: {end_payload}\n\n"
        except Exception as e:
            err_payload = json.dumps({"error": str(e), "done": True})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── 3. Provider List & Status ─────────────────────────────────
@router.get("/providers")
async def get_providers():
    """Returns all AI providers with live status and metadata."""
    statuses = await ai_manager.get_all_provider_statuses()
    return {"providers": [s.model_dump() for s in statuses]}


# ─── 4. Model Registry ─────────────────────────────────────────
@router.get("/models")
async def get_models(
    provider: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    available_only: bool = Query(False),
):
    """Returns registered models with verified capabilities and live availability."""
    models = await ai_manager.get_models()
    if provider:
        models = [m for m in models if m.provider == provider]
    if location:
        models = [m for m in models if m.location == location]
    if available_only:
        models = [m for m in models if m.available]
    return {"models": [m.model_dump() for m in models]}


# ─── 5. Route Simulation ───────────────────────────────────────
@router.post("/route")
async def evaluate_route(req: RouteRequest):
    """
    Dry-run simulation of the Smart AI Router for a given request.
    Shows task classification, privacy detection, and routing reasons.
    """
    messages = _normalize_messages(req)
    decision = await ai_router.route(
        messages=messages,
        user_mode=req.mode,
        requested_provider=req.provider,
        requested_model=req.model,
        attachments=req.attachments,
        allow_cloud_override=req.allow_cloud_override,
    )
    online = await ai_router.is_online()
    ollama_ok = await ai_router.is_ollama_available()

    return {
        "provider": decision.provider,
        "model": decision.model,
        "mode": decision.mode,
        "reasons": decision.reasons,
        "privacy_warning": decision.privacy_warning,
        "is_fallback": decision.is_fallback,
        "explanation": decision.to_reason_string(),
        "internet_connected": online,
        "ollama_available": ollama_ok,
    }


# ─── 6. Provider Health Checks ─────────────────────────────────
@router.post("/health")
async def health_check_all():
    """Runs health check across all registered AI providers."""
    statuses = await ai_manager.get_all_provider_statuses()
    all_ok = any(s.available for s in statuses)
    return {
        "status": "healthy" if all_ok else "degraded",
        "providers": [s.model_dump() for s in statuses],
    }


# ─── 7. Provider Test Connection ───────────────────────────────
@router.post("/provider/test")
async def test_single_provider(req: ProviderTestRequest):
    """Tests connection and measures actual latency to a single provider."""
    result = await ai_manager.test_provider(req.provider, req.prompt or "Hello from SnapAI Edge")
    return result


# ─── 8. System AI Status ───────────────────────────────────────
@router.get("/status")
async def ai_system_status():
    """
    Comprehensive system status:
    - Providers status
    - Active routing mode
    - Hardware acceleration info
    - Network status
    - Installed local models
    """
    online = await ai_router.is_online()
    ollama_ok = await ai_router.is_ollama_available()
    installed_ollama = await ai_router.get_installed_ollama_models() if ollama_ok else []
    
    local_p: LocalProvider = ai_manager.get_provider(ProviderType.LOCAL.value)
    hw = local_p.detect_hardware() if local_p else {}

    providers_status = await ai_manager.get_all_provider_statuses()

    # Active recommended mode
    if not online:
        active_mode = "offline"
    elif ollama_ok and installed_ollama:
        active_mode = "local"
    elif any(p.configured and p.available for p in providers_status if p.type == "cloud"):
        active_mode = "cloud"
    else:
        active_mode = "local"

    return {
        "system": "SnapAI Edge",
        "online": online,
        "active_mode": active_mode,
        "default_privacy_mode": ai_router.privacy,
        "providers": [p.model_dump() for p in providers_status],
        "local_models_available": len(installed_ollama),
        "installed_local_models": installed_ollama,
        "hardware": {
            "is_snapdragon": hw.get("is_snapdragon", False),
            "snapdragon_status": hw.get("snapdragon_status", "UNAVAILABLE"),
            "architecture": hw.get("architecture", "Unknown"),
            "cpu_brand": hw.get("cpu_brand", "Unknown"),
            "gpu_name": hw.get("gpu_name"),
            "verified_device": hw.get("verified_device", "CPU"),
            "acceleration_verified": hw.get("acceleration_verified", False),
            "runtimes": hw.get("runtimes", {}),
        },
    }


# ─── 9. Privacy Scan Endpoint ──────────────────────────────────
@router.post("/privacy/scan")
async def scan_privacy(req: PrivacyScanRequest):
    """Analyze input text for sensitive patterns before submission."""
    res = privacy_guard.scan(req.text)
    masked = privacy_guard.mask(req.text)
    return {
        "has_sensitive_data": res.has_sensitive_data,
        "detected_categories": res.detected_categories,
        "risk_level": res.risk_level,
        "warning": res.warning,
        "masked_preview": masked[:200],
    }


# ─── 10. Conversation Management Endpoints (Preserved) ─────────
@router.get("/conversations")
async def list_conversations(db: Session = Depends(get_db)):
    convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at, "updated_at": c.updated_at}
        for c in convs
    ]


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "mode": m.mode,
            "model": m.model,
            "latency_ms": m.latency_ms,
            "created_at": m.created_at,
        }
        for m in msgs
    ]


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter_by(id=conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()
    return {"deleted": conv_id}
