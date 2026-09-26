"""
SnapAI Edge - Unified AI Package
Exports types, base provider, model manager, router, model registry, and metrics.
"""

from ai.types import (
    ProviderType,
    UserMode,
    ModelCapability,
    HardwareStatus,
    UnifiedResponse,
    ModelInfo,
    ProviderStatus,
)
from ai.base import AIProvider
from ai.manager import ai_manager, AIModelManager
from ai.router import router as ai_router, AIRouter, RoutingDecision
from ai.models.registry import model_registry, AIModelRegistry
from ai.metrics import metrics_tracker, PerformanceMetric

__all__ = [
    "ProviderType",
    "UserMode",
    "ModelCapability",
    "HardwareStatus",
    "UnifiedResponse",
    "ModelInfo",
    "ProviderStatus",
    "AIProvider",
    "ai_manager",
    "AIModelManager",
    "ai_router",
    "AIRouter",
    "RoutingDecision",
    "model_registry",
    "AIModelRegistry",
    "metrics_tracker",
    "PerformanceMetric",
]
