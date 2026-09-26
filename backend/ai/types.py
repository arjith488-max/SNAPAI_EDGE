"""
SnapAI Edge - AI Abstraction Layer Types
Defines provider types, capabilities, user modes, hardware status, and the unified response format.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    LOCAL = "local"


class UserMode(str, Enum):
    AUTO = "auto"
    LOCAL_FIRST = "local_first"
    CLOUD_FIRST = "cloud_first"
    HYBRID = "hybrid"
    OFFLINE_ONLY = "offline_only"


class ModelCapability(str, Enum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    EMBEDDING = "embedding"
    REASONING = "reasoning"
    CODING = "coding"
    DOCUMENT = "document"
    STREAMING = "streaming"


class HardwareStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class UnifiedResponse(BaseModel):
    """
    Normalized response structure returned by all AI providers.
    Never fabricates metrics.
    """
    provider: str
    model: str
    mode: str  # "local" | "cloud" | "hybrid" | "offline"
    response: str
    latency_ms: float
    streaming: bool = False
    network_used: bool = False
    local_processing: bool = True
    routing_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelInfo(BaseModel):
    """
    Unified model metadata for the AI Model Registry.
    """
    id: str  # e.g., "ollama:llama3.2", "openai:gpt-4o-mini", "gemini:gemini-1.5-flash"
    provider: str
    name: str
    location: str  # "local" | "cloud"
    capabilities: List[str] = Field(default_factory=lambda: ["text"])
    streaming: bool = True
    vision: bool = False
    embedding: bool = False
    available: bool = False
    description: Optional[str] = None
    quantization: Optional[str] = None
    context_length: Optional[int] = None
    size_mb: Optional[float] = None
    hardware_accelerated: bool = False


class ProviderStatus(BaseModel):
    """
    Status of an AI provider.
    """
    provider: str
    name: str
    type: str  # "cloud" | "local"
    available: bool
    configured: bool
    status_text: str
    models_count: int = 0
    active_model: Optional[str] = None
    endpoint: Optional[str] = None
    hardware_status: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
