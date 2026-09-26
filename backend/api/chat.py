"""SnapAI Edge - Chat API Router"""

import uuid
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.db import get_db, Conversation, Message
from ai.router import router as ai_router

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    prefer_local: bool = False
    attachments: Optional[list] = []


class ConversationCreate(BaseModel):
    title: str = "New Conversation"


@router.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    # Get or create conversation
    conv_id = req.conversation_id or str(uuid.uuid4())
    conv = db.query(Conversation).filter_by(id=conv_id).first()
    if not conv:
        conv = Conversation(id=conv_id, title=req.message[:60])
        db.add(conv)
        db.commit()

    # Load history (last 10 messages for context)
    history = db.query(Message).filter_by(conversation_id=conv_id).order_by(Message.created_at.desc()).limit(10).all()
    messages = [{"role": m.role, "content": m.content} for m in reversed(history)]
    messages.append({"role": "user", "content": req.message})

    # Build system message
    system = {
        "role": "system",
        "content": (
            "You are SnapAI Edge, a private multimodal AI assistant optimized for Snapdragon-powered HP PCs. "
            "You help users with text, images, documents, code, and more. "
            "Be concise, accurate, and helpful. When you don't know something, say so clearly."
        )
    }
    full_messages = [system] + messages

    # Route to AI
    result = await ai_router.chat(full_messages, model=req.model, prefer_local=req.prefer_local)

    # Save user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=req.message,
        attachments=str(req.attachments) if req.attachments else None,
    )
    db.add(user_msg)

    # Save assistant message
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="assistant",
        content=result.get("content", ""),
        mode=result.get("mode", "unknown"),
        model=result.get("model"),
        latency_ms=result.get("latency_ms"),
    )
    db.add(assistant_msg)

    # Update conversation title from first message
    if conv.title == "New Conversation":
        conv.title = req.message[:60]
    db.commit()

    return {
        "conversation_id": conv_id,
        "message_id": assistant_msg.id,
        "content": result.get("content", ""),
        "mode": result.get("mode", "unknown"),
        "model": result.get("model"),
        "latency_ms": result.get("latency_ms"),
        "provider": result.get("provider"),
        "processed_locally": result.get("processed_locally", False),
    }


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


@router.patch("/conversations/{conv_id}")
async def rename_conversation(conv_id: str, body: ConversationCreate, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter_by(id=conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    conv.title = body.title
    db.commit()
    return {"id": conv_id, "title": conv.title}


@router.post("/route")
async def route_info():
    """Returns current routing decision and provider status."""
    online = await ai_router.is_online()
    ollama = await ai_router.is_ollama_available()
    return {
        "internet": online,
        "ollama_available": ollama,
        "jina_configured": bool(ai_router.jina_key),
        "openai_configured": bool(ai_router.openai_key),
        "privacy_mode": ai_router.privacy,
        "cloud_enabled": ai_router.cloud_enabled,
        "recommended_mode": (
            "local" if ollama else
            "cloud" if (online and ai_router.jina_key) else
            "offline"
        ),
    }
