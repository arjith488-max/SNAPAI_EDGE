"""
SnapAI Edge - AI Model Manager
Coordinates providers, model discovery, health checks, routing execution, streaming, and error fallback.
"""

import time
from typing import Dict, List, Any, Optional, AsyncGenerator

from ai.base import AIProvider
from ai.types import (
    ProviderType,
    UserMode,
    UnifiedResponse,
    ModelInfo,
    ProviderStatus,
)
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.local_provider import LocalProvider
from ai.models.registry import model_registry
from ai.router import router as ai_router, RoutingDecision
from ai.metrics import metrics_tracker


class AIModelManager:
    """
    Central Manager for all AI operations in SnapAI Edge.
    """

    def __init__(self):
        self._providers: Dict[str, AIProvider] = {
            ProviderType.OPENAI.value: OpenAIProvider(),
            ProviderType.GEMINI.value: GeminiProvider(),
            ProviderType.OLLAMA.value: OllamaProvider(),
            ProviderType.LOCAL.value: LocalProvider(),
        }

    def get_provider(self, provider_id: str) -> Optional[AIProvider]:
        """Fetch provider instance by id."""
        return self._providers.get(provider_id.lower())

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())

    async def get_all_provider_statuses(self) -> List[ProviderStatus]:
        """Run health check across all registered providers."""
        statuses = []
        for p_id, provider in self._providers.items():
            try:
                st = await provider.health_check()
                statuses.append(st)
                # If provider is Ollama and running, sync its models with registry
                if p_id == ProviderType.OLLAMA.value and st.available:
                    installed = await provider.get_installed_models()
                    model_registry.sync_ollama_models(installed)
                elif p_id in (ProviderType.OPENAI.value, ProviderType.GEMINI.value):
                    for m in provider.get_models():
                        model_registry.set_availability(m.id, st.available)
            except Exception as e:
                statuses.append(
                    ProviderStatus(
                        provider=p_id,
                        name=provider.provider_name,
                        type="local" if provider.is_local else "cloud",
                        available=False,
                        configured=False,
                        status_text=f"Health check failed: {str(e)}",
                        error=str(e),
                    )
                )
        return statuses

    async def get_models(self) -> List[ModelInfo]:
        """Return unified list of models from the registry with live availability."""
        # Refresh Ollama models if running
        ollama_p: OllamaProvider = self._providers[ProviderType.OLLAMA.value]
        installed = await ollama_p.get_installed_models()
        model_registry.sync_ollama_models(installed)

        # Update cloud availability
        openai_p = self._providers[ProviderType.OPENAI.value]
        gemini_p = self._providers[ProviderType.GEMINI.value]
        local_p = self._providers[ProviderType.LOCAL.value]

        for m in openai_p.get_models():
            model_registry.register(m)
        for m in gemini_p.get_models():
            model_registry.register(m)
        for m in local_p.get_models():
            model_registry.register(m)

        return model_registry.list_all()

    async def test_provider(self, provider_id: str, prompt: str = "Hello from SnapAI Edge") -> Dict[str, Any]:
        """Test connection to a specific provider and measure live latency."""
        provider = self.get_provider(provider_id)
        if not provider:
            return {"provider": provider_id, "success": False, "error": f"Unknown provider: {provider_id}"}

        start = time.time()
        try:
            status = await provider.health_check()
            if not status.available:
                return {
                    "provider": provider_id,
                    "success": False,
                    "status": status.model_dump(),
                    "error": status.error or status.status_text,
                }

            # Run simple generate test
            test_resp = await provider.generate([{"role": "user", "content": prompt}])
            latency_ms = round((time.time() - start) * 1000, 1)

            has_err = "error" in test_resp.metadata or test_resp.response.startswith("[OpenAI Error") or test_resp.response.startswith("[Gemini Error")
            return {
                "provider": provider_id,
                "success": not has_err,
                "latency_ms": latency_ms,
                "response_sample": test_resp.response[:120],
                "mode": test_resp.mode,
                "model": test_resp.model,
                "status": status.model_dump(),
                "error": test_resp.metadata.get("error") if has_err else None,
            }
        except Exception as e:
            return {
                "provider": provider_id,
                "success": False,
                "latency_ms": round((time.time() - start) * 1000, 1),
                "error": str(e),
            }

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        provider: str = "auto",
        mode: str = UserMode.AUTO.value,
        model: Optional[str] = None,
        attachments: Optional[List[Any]] = None,
        allow_cloud_override: bool = False,
        **kwargs,
    ) -> UnifiedResponse:
        """
        Unified generation method.
        Routes request using Smart AI Router, handles provider execution and safe fallbacks.
        """
        # Route request
        decision: RoutingDecision = await ai_router.route(
            messages=messages,
            user_mode=mode,
            requested_provider=provider,
            requested_model=model,
            attachments=attachments,
            allow_cloud_override=allow_cloud_override,
        )

        chosen_provider = self.get_provider(decision.provider)
        if not chosen_provider:
            return UnifiedResponse(
                provider=decision.provider,
                model=decision.model,
                mode=decision.mode,
                response=f"Requested provider '{decision.provider}' is not supported.",
                latency_ms=0.0,
                streaming=False,
                network_used=False,
                local_processing=False,
                routing_reason=decision.to_reason_string(),
                metadata={"error": "unsupported_provider"},
            )

        # Execute chosen provider
        resp = await chosen_provider.generate(
            messages=messages,
            model=decision.model,
            routing_reason=decision.to_reason_string(),
            attachments=attachments,
            **kwargs,
        )

        # Check if execution failed
        is_error = "error" in resp.metadata

        # Section 20 requirement:
        # If user explicitly selected a provider and it fails:
        # DO NOT silently switch! Prompt user: "[Retry] [Switch to Auto]"
        if is_error and provider != "auto":
            resp.response = (
                f"{chosen_provider.provider_name} request failed.\n\n"
                f"Error: {resp.metadata.get('details') or resp.response}\n\n"
                f"[Retry]  [Switch to Auto]"
            )
            resp.routing_reason = decision.to_reason_string()
            return resp

        # If user is in AUTO mode and primary selection failed, attempt safe fallback
        if is_error and provider == "auto":
            fallback_provider_id = (
                ProviderType.OPENAI.value if decision.provider == ProviderType.GEMINI.value else
                ProviderType.GEMINI.value if decision.provider == ProviderType.OPENAI.value else
                ProviderType.LOCAL.value
            )
            fb_provider = self.get_provider(fallback_provider_id)
            if fb_provider and fb_provider.is_configured():
                fallback_reason = f"Fallback to {fb_provider.provider_name} because {chosen_provider.provider_name} encountered an error."
                fallback_resp = await fb_provider.generate(
                    messages=messages,
                    routing_reason=f"{decision.to_reason_string()}\n✓ {fallback_reason}",
                    attachments=attachments,
                    **kwargs,
                )
                if "error" not in fallback_resp.metadata:
                    fallback_resp.routing_reason = f"{decision.to_reason_string()}\n✓ {fallback_reason}"
                    return fallback_resp

        resp.routing_reason = decision.to_reason_string()
        return resp

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        provider: str = "auto",
        mode: str = UserMode.AUTO.value,
        model: Optional[str] = None,
        attachments: Optional[List[Any]] = None,
        allow_cloud_override: bool = False,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Unified streaming generation method.
        Routes request and streams chunks from the selected provider.
        """
        decision: RoutingDecision = await ai_router.route(
            messages=messages,
            user_mode=mode,
            requested_provider=provider,
            requested_model=model,
            attachments=attachments,
            allow_cloud_override=allow_cloud_override,
        )

        chosen_provider = self.get_provider(decision.provider)
        if not chosen_provider:
            yield f"[Error: Provider '{decision.provider}' not available]"
            return

        async for chunk in chosen_provider.stream(
            messages=messages,
            model=decision.model,
            routing_reason=decision.to_reason_string(),
            attachments=attachments,
            **kwargs,
        ):
            yield chunk


# Singleton AI Manager
ai_manager = AIModelManager()
