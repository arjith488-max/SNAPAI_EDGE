"""
SnapAI Edge - Ollama Local AI Provider
Connects to local Ollama daemon for 100% private, on-device edge inference.
Measures local latency, discovers installed models, supports streaming, and handles offline mode.
Never downloads large models without explicit user approval.
"""

import os
import json
import time
import httpx
from typing import AsyncGenerator, List, Dict, Any, Optional
from dotenv import load_dotenv

from ai.base import AIProvider
from ai.types import UnifiedResponse, ModelInfo, ProviderStatus, ProviderType, ModelCapability
from ai.metrics import metrics_tracker, PerformanceMetric

load_dotenv()


class OllamaProvider(AIProvider):
    """
    Ollama Local Provider implementation.
    """

    def __init__(self):
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self._default_model = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
        self._installed_models: List[str] = []
        self._is_running = False

    @property
    def provider_id(self) -> str:
        return ProviderType.OLLAMA.value

    @property
    def provider_name(self) -> str:
        return "Ollama (Local)"

    @property
    def is_local(self) -> bool:
        return True

    def _get_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", self._base_url).rstrip("/")

    def _get_default_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", self._default_model).strip() or "llama3.2"

    async def get_installed_models(self) -> List[str]:
        """Query Ollama daemon for currently installed models."""
        base_url = self._get_base_url()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    self._installed_models = models
                    self._is_running = True
                    return models
        except Exception:
            self._is_running = False
        return []

    async def is_model_installed(self, model_name: str) -> bool:
        """Check if a specific model or model:tag is installed locally."""
        installed = await self.get_installed_models()
        # Direct match or prefix match (e.g. "llama3.2" matching "llama3.2:latest")
        clean_target = model_name.split(":", 1)[-1] if ":" in model_name else model_name
        for m in installed:
            if m == clean_target or m.split(":")[0] == clean_target:
                return True
        return False

    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> UnifiedResponse:
        base_url = self._get_base_url()
        requested_model = kwargs.get("model") or self._get_default_model()
        # Clean model name (e.g. "ollama:llama3.2" -> "llama3.2")
        model = requested_model.split(":", 1)[1] if requested_model.startswith("ollama:") else requested_model

        # Health & existence check
        installed = await self.get_installed_models()
        if not self._is_running:
            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="offline" if kwargs.get("offline_mode") else "local",
                response=(
                    "Ollama is not running. Please start Ollama locally (`ollama serve`) "
                    f"to enable offline local inference with '{model}'."
                ),
                latency_ms=0.0,
                streaming=False,
                network_used=False,
                local_processing=True,
                routing_reason="Ollama daemon not running",
                metadata={"error": "ollama_not_running"},
            )

        # Check if the requested model is installed
        matched_model = None
        for m in installed:
            if m == model or m.split(":")[0] == model:
                matched_model = m
                break

        if not matched_model:
            # Fallback to any installed model if available
            if installed:
                fallback_msg = (
                    f"Requested model '{model}' is not installed in Ollama. "
                    f"Installed models: {', '.join(installed)}. "
                    f"To install run: `ollama pull {model}`."
                )
            else:
                fallback_msg = (
                    f"No models installed in Ollama. "
                    f"Run `ollama pull {model}` to install a local model."
                )
            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="local",
                response=fallback_msg,
                latency_ms=0.0,
                streaming=False,
                network_used=False,
                local_processing=True,
                routing_reason="Model not installed",
                metadata={"error": "model_not_installed", "installed_models": installed},
            )

        # Format messages for Ollama /api/chat
        formatted_messages = []
        for m in messages:
            formatted_messages.append({
                "role": m.get("role", "user"),
                "content": str(m.get("content", "")),
            })

        start_time = time.time()
        system_snapshot_before = metrics_tracker.get_system_snapshot()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": matched_model,
                        "messages": formatted_messages,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            latency_ms = round((time.time() - start_time) * 1000, 1)
            content = data.get("message", {}).get("content", "")

            # Genuine metrics returned by Ollama
            eval_count = data.get("eval_count")
            eval_duration_ns = data.get("eval_duration")
            tps = None
            if eval_count and eval_duration_ns:
                tps = round(eval_count / (eval_duration_ns / 1e9), 1)

            metric_meta = {
                "eval_count": eval_count,
                "eval_duration_ms": round(eval_duration_ns / 1e6, 1) if eval_duration_ns else None,
                "load_duration_ms": round(data.get("load_duration", 0) / 1e6, 1),
                "system_before": system_snapshot_before,
            }

            metrics_tracker.record(
                PerformanceMetric(
                    provider=self.provider_id,
                    model=matched_model,
                    mode="local",
                    latency_ms=latency_ms,
                    token_count=eval_count,
                    tokens_per_second=tps,
                    memory_used_mb=system_snapshot_before.get("process_rss_mb"),
                    cpu_percent=system_snapshot_before.get("system_cpu_percent"),
                    network_used=False,
                    metadata=metric_meta,
                )
            )

            return UnifiedResponse(
                provider=self.provider_id,
                model=matched_model,
                mode="local",
                response=content,
                latency_ms=latency_ms,
                streaming=False,
                network_used=False,
                local_processing=True,
                routing_reason=kwargs.get("routing_reason") or "Executed on local device via Ollama",
                metadata=metric_meta,
            )

        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            return UnifiedResponse(
                provider=self.provider_id,
                model=matched_model,
                mode="local",
                response=f"Ollama execution error: {str(e)}",
                latency_ms=latency_ms,
                network_used=False,
                local_processing=True,
                metadata={"error": "ollama_execution_failed", "details": str(e)},
            )

    async def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        base_url = self._get_base_url()
        requested_model = kwargs.get("model") or self._get_default_model()
        model = requested_model.split(":", 1)[1] if requested_model.startswith("ollama:") else requested_model

        installed = await self.get_installed_models()
        if not self._is_running:
            yield "Ollama is not running. Please start Ollama locally (`ollama serve`)."
            return

        matched_model = None
        for m in installed:
            if m == model or m.split(":")[0] == model:
                matched_model = m
                break

        if not matched_model:
            yield f"Model '{model}' is not installed locally. Run `ollama pull {model}` to install."
            return

        formatted_messages = [
            {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
            for m in messages
        ]

        start_time = time.time()
        first_token_time = None
        token_count = 0

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/chat",
                    json={
                        "model": matched_model,
                        "messages": formatted_messages,
                        "stream": True,
                        "options": {"temperature": kwargs.get("temperature", 0.7)},
                    },
                ) as stream_resp:
                    stream_resp.raise_for_status()
                    async for line in stream_resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                token_count += 1
                                yield token
                        except Exception:
                            continue

            total_ms = round((time.time() - start_time) * 1000, 1)
            ttft_ms = round((first_token_time - start_time) * 1000, 1) if first_token_time else None
            tps = round(token_count / ((time.time() - start_time) or 0.001), 1)

            metrics_tracker.record(
                PerformanceMetric(
                    provider=self.provider_id,
                    model=matched_model,
                    mode="local",
                    latency_ms=total_ms,
                    time_to_first_token_ms=ttft_ms,
                    total_time_ms=total_ms,
                    token_count=token_count,
                    tokens_per_second=tps,
                    network_used=False,
                )
            )

        except Exception as e:
            yield f"\n[Ollama Streaming Error: {str(e)}]"

    async def health_check(self) -> ProviderStatus:
        base_url = self._get_base_url()
        start = time.time()
        installed = await self.get_installed_models()
        latency = round((time.time() - start) * 1000, 1)

        if self._is_running:
            return ProviderStatus(
                provider=self.provider_id,
                name=self.provider_name,
                type="local",
                available=True,
                configured=True,
                status_text=f"Running ({len(installed)} models installed)",
                models_count=len(installed),
                active_model=self._get_default_model(),
                endpoint=base_url,
                latency_ms=latency,
            )
        else:
            return ProviderStatus(
                provider=self.provider_id,
                name=self.provider_name,
                type="local",
                available=False,
                configured=True,
                status_text="Not running (daemon unreachable at localhost:11434)",
                models_count=0,
                active_model=self._get_default_model(),
                endpoint=base_url,
                latency_ms=latency,
                error="Daemon unreachable",
            )

    def get_models(self) -> List[ModelInfo]:
        """Return ModelInfo for installed Ollama models, or known defaults if none installed."""
        default_model = self._get_default_model()
        if self._installed_models:
            models = []
            for name in self._installed_models:
                is_vision = "llava" in name.lower() or "vision" in name.lower()
                caps = [ModelCapability.TEXT.value, ModelCapability.STREAMING.value]
                if is_vision:
                    caps.append(ModelCapability.VISION.value)
                models.append(
                    ModelInfo(
                        id=f"ollama:{name}",
                        provider=self.provider_id,
                        name=name,
                        location="local",
                        capabilities=caps,
                        streaming=True,
                        vision=is_vision,
                        embedding=False,
                        available=True,
                        description=f"Local Ollama model: {name}",
                    )
                )
            return models

        # Known catalog entry showing download required
        return [
            ModelInfo(
                id=f"ollama:{default_model}",
                provider=self.provider_id,
                name=default_model,
                location="local",
                capabilities=[ModelCapability.TEXT.value, ModelCapability.STREAMING.value],
                streaming=True,
                vision=False,
                embedding=False,
                available=False,
                description=f"Local model (pull via `ollama pull {default_model}`)",
            )
        ]

    def get_capabilities(self) -> List[str]:
        caps = [ModelCapability.TEXT.value, ModelCapability.STREAMING.value]
        if any("llava" in m.lower() or "vision" in m.lower() for m in self._installed_models):
            caps.append(ModelCapability.VISION.value)
        return caps
