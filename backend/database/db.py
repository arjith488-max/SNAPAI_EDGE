"""
SnapAI Edge - SQLite Database Layer
Handles all persistent storage: conversations, messages, documents, settings, benchmarks.
"""

import os
import json
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float,
    Text, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./snapai.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Models ───────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"
    id          = Column(String, primary_key=True)
    title       = Column(String, default="New Conversation")
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages    = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id              = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role            = Column(String, nullable=False)   # user | assistant | system
    content         = Column(Text, nullable=False)
    mode            = Column(String, default="cloud")  # local | cloud | hybrid
    model           = Column(String, nullable=True)
    latency_ms      = Column(Float, nullable=True)
    attachments     = Column(Text, nullable=True)       # JSON list
    created_at      = Column(DateTime, default=datetime.utcnow)
    conversation    = relationship("Conversation", back_populates="messages")


class Document(Base):
    __tablename__ = "documents"
    id           = Column(String, primary_key=True)
    filename     = Column(String, nullable=False)
    original_name= Column(String, nullable=False)
    file_type    = Column(String, nullable=False)
    file_size    = Column(Integer, nullable=False)
    page_count   = Column(Integer, nullable=True)
    char_count   = Column(Integer, nullable=True)
    chunk_count  = Column(Integer, nullable=True)
    collection   = Column(String, default="default")
    indexed      = Column(Boolean, default=False)
    index_status = Column(String, default="pending")  # pending|indexing|ready|error
    upload_path  = Column(String, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    id            = Column(String, primary_key=True)
    test_name     = Column(String, nullable=False)
    model         = Column(String, nullable=False)
    mode          = Column(String, nullable=False)  # local | cloud
    latency_ms    = Column(Float, nullable=False)
    memory_mb     = Column(Float, nullable=True)
    input_tokens  = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    success       = Column(Boolean, default=True)
    error         = Column(String, nullable=True)
    raw_metrics   = Column(Text, nullable=True)   # JSON
    created_at    = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key        = Column(String, primary_key=True)
    value      = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Init ─────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Seed default settings
    defaults = {
        "privacy_mode": "local_first",
        "cloud_enabled": "true",
        "telemetry": "false",
        "ai_mode": "hybrid",
        "default_model": "jina",
        "voice_enabled": "true",
        "camera_enabled": "true",
    }
    for k, v in defaults.items():
        if not db.query(Setting).filter_by(key=k).first():
            db.add(Setting(key=k, value=v))
    db.commit()
    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
