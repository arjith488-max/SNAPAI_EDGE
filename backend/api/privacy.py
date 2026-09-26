"""SnapAI Edge - Privacy & Settings API"""

import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db, Setting

router = APIRouter()


class PrivacySettings(BaseModel):
    privacy_mode: str = "local_first"  # local_first | cloud_first | hybrid | offline
    cloud_enabled: bool = True
    telemetry: bool = False


@router.get("/status")
async def privacy_status(db: Session = Depends(get_db)):
    keys = ["privacy_mode", "cloud_enabled", "telemetry", "ai_mode"]
    settings = {s.key: s.value for s in db.query(Setting).filter(Setting.key.in_(keys)).all()}
    return {
        "privacy_mode": settings.get("privacy_mode", "local_first"),
        "cloud_enabled": settings.get("cloud_enabled", "true") == "true",
        "telemetry": settings.get("telemetry", "false") == "true",
        "local_processing": settings.get("privacy_mode") in ("local_first", "offline"),
        "cloud_processing": settings.get("cloud_enabled", "true") == "true",
        "camera_enabled": os.getenv("ENABLE_CAMERA", "true") == "true",
        "voice_enabled": os.getenv("ENABLE_VOICE", "true") == "true",
        "data_storage": "local_only",
        "api_key_stored": "environment_variable_only",
    }


@router.post("/settings")
async def update_privacy(body: PrivacySettings, db: Session = Depends(get_db)):
    updates = {
        "privacy_mode": body.privacy_mode,
        "cloud_enabled": str(body.cloud_enabled).lower(),
        "telemetry": str(body.telemetry).lower(),
    }
    for k, v in updates.items():
        s = db.query(Setting).filter_by(key=k).first()
        if s:
            s.value = v
        else:
            db.add(Setting(key=k, value=v))
    db.commit()
    return {"status": "updated", "settings": updates}


@router.post("/clear/conversations")
async def clear_conversations(db: Session = Depends(get_db)):
    from database.db import Conversation, Message
    db.query(Message).delete()
    db.query(Conversation).delete()
    db.commit()
    return {"cleared": "conversations"}


@router.post("/clear/documents")
async def clear_documents(db: Session = Depends(get_db)):
    import shutil
    from database.db import Document
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    docs = db.query(Document).all()
    for d in docs:
        if os.path.exists(d.upload_path):
            os.remove(d.upload_path)
    db.query(Document).delete()
    db.commit()
    # Clear ChromaDB
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        for col in client.list_collections():
            client.delete_collection(col.name)
    except Exception:
        pass
    return {"cleared": "documents"}


@router.post("/clear/all")
async def clear_all(db: Session = Depends(get_db)):
    await clear_conversations(db)
    await clear_documents(db)
    return {"cleared": "all_data"}
