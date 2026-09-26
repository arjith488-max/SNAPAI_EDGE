"""
SnapAI Edge - Common AI Provider Interface
Defines the abstract base class that every AI provider must implement.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional
from ai.types import UnifiedResponse, ModelInfo, ProviderStatus


class AIProvider(ABC):
    """
    Common AI Provider Interface.
    Every provider (OpenAI, Gemini, Ollama, Local) must implement this interface.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return provider identifier (e.g. 'openai', 'gemini', 'ollama', 'local')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return human-readable provider name."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Return True if this provider runs inference entirely on the local device."""
        pass

    @abstractmethod
    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> UnifiedResponse:
        """
        Execute normal text generation.
        Returns a normalized UnifiedResponse.
        """
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        """
        Execute streaming text generation yielding tokens or chunks as they arrive.
        """
        pass

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """
        Check health and connectivity of the provider.
        """
        pass

    @abstractmethod
    def get_models(self) -> List[ModelInfo]:
        """
        Return the list of models supported/installed for this provider.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Return capabilities supported by this provider.
        """
        pass
