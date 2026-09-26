"""
SnapAI Edge - OpenAI Provider
Official OpenAI SDK integration with streaming, multimodal input, error sanitization, and latency capture.
Never exposes API keys in logs or responses.
"""

import os
import time
from typing import AsyncGenerator, List, Dict, Any, Optional
from dotenv import load_dotenv

from ai.base import AIProvider
from ai.types import UnifiedResponse, ModelInfo, ProviderStatus, ProviderType, ModelCapability
from ai.metrics import metrics_tracker, PerformanceMetric

load_dotenv()

try:
    from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError, APIConnectionError
except ImportError:
    AsyncOpenAI = None
    APIError = Exception
    AuthenticationError = Exception
    RateLimitError = Exception
    APIConnectionError = Exception


class OpenAIProvider(AIProvider):
    """
    OpenAI Cloud Provider implementation.
    """

    def __init__(self):
        self._api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self._base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        self._client: Optional[Any] = None

    @property
    def provider_id(self) -> str:
        return ProviderType.OPENAI.value

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    @property
    def is_local(self) -> bool:
        return False

    def _get_client(self) -> Optional[Any]:
        # Always check os.environ or load_dotenv if missing
        if "OPENAI_API_KEY" in os.environ:
            self._api_key = os.environ["OPENAI_API_KEY"].strip()
        elif not self._api_key:
            load_dotenv()
            self._api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self._api_key or AsyncOpenAI is None:
            return None
        if self._client is None or getattr(self._client, "_api_key", None) != self._api_key:
            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def is_configured(self) -> bool:
        if "OPENAI_API_KEY" in os.environ:
            return bool(os.environ["OPENAI_API_KEY"].strip())
        load_dotenv()
        return bool(os.getenv("OPENAI_API_KEY", "").strip())

    def _sanitize_error(self, err: Exception) -> str:
        msg = str(err)
        # Strip any accidental API key occurrences
        if self._api_key and len(self._api_key) > 5:
            msg = msg.replace(self._api_key, "[REDACTED_API_KEY]")
        return msg

    def _format_messages(self, messages: List[Dict[str, Any]], model: str) -> List[Dict[str, Any]]:
        """
        Normalize messages and check multimodal capabilities.
        If model doesn't support vision, strip image payloads to avoid API error.
        """
        is_vision_model = any(vm in model.lower() for vm in ["gpt-4o", "vision", "gpt-4-turbo"])
        formatted = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            attachments = m.get("attachments", [])

            if attachments and is_vision_model:
                parts = [{"type": "text", "text": str(content)}]
                for att in attachments:
                    if isinstance(att, dict) and "url" in att:
                        parts.append({"type": "image_url", "image_url": {"url": att["url"]}})
                    elif isinstance(att, str) and (att.startswith("http") or att.startswith("data:image")):
                        parts.append({"type": "image_url", "image_url": {"url": att}})
                formatted.append({"role": role, "content": parts})
            else:
                # Flat string representation
                text_content = content if isinstance(content, str) else str(content)
                formatted.append({"role": role, "content": text_content})
        return formatted

    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> UnifiedResponse:
        client = self._get_client()
        if not client:
            return UnifiedResponse(
                provider=self.provider_id,
                model=kwargs.get("model", self._default_model),
                mode="cloud",
                response="OpenAI API key is not configured. Please add OPENAI_API_KEY in your settings or .env file.",
                latency_ms=0.0,
                streaming=False,
                network_used=False,
                local_processing=False,
                routing_reason="OpenAI unconfigured",
                metadata={"error": "OPENAI_API_KEY missing"},
            )

        model = kwargs.get("model") or self._default_model
        formatted_messages = self._format_messages(messages, model)
        temperature = kwargs.get("temperature", 0.7)

        start_time = time.time()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
            )
            latency_ms = round((time.time() - start_time) * 1000, 1)
            content = resp.choices[0].message.content or ""

            usage_info = {}
            if resp.usage:
                usage_info = {
                    "prompt_tokens": resp.usage.prompt_tokens,
                    "completion_tokens": resp.usage.completion_tokens,
                    "total_tokens": resp.usage.total_tokens,
                }

            metrics_tracker.record(
                PerformanceMetric(
                    provider=self.provider_id,
                    model=model,
                    mode="cloud",
                    latency_ms=latency_ms,
                    token_count=usage_info.get("completion_tokens"),
                    network_used=True,
                    metadata=usage_info,
                )
            )

            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="cloud",
                response=content,
                latency_ms=latency_ms,
                streaming=False,
                network_used=True,
                local_processing=False,
                routing_reason=kwargs.get("routing_reason"),
                metadata=usage_info,
            )

        except AuthenticationError as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="cloud",
                response=f"OpenAI Authentication Failed: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "authentication_error", "details": sanitized},
            )
        except RateLimitError as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="cloud",
                response=f"OpenAI Rate Limit Exceeded: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "rate_limit_error", "details": sanitized},
            )
        except APIConnectionError as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="cloud",
                response=f"OpenAI Connection Error: Unable to reach OpenAI servers ({sanitized})",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "connection_error", "details": sanitized},
            )
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model,
                mode="cloud",
                response=f"OpenAI Request Error: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "api_error", "details": sanitized},
            )

    async def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        client = self._get_client()
        if not client:
            yield "OpenAI API key is not configured. Please add OPENAI_API_KEY in your settings."
            return

        model = kwargs.get("model") or self._default_model
        formatted_messages = self._format_messages(messages, model)
        temperature = kwargs.get("temperature", 0.7)

        start_time = time.time()
        first_token_time = None
        token_count = 0

        try:
            stream_resp = await client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream_resp:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    if first_token_time is None:
                        first_token_time = time.time()
                    token_count += 1
                    yield token

            total_ms = round((time.time() - start_time) * 1000, 1)
            ttft_ms = round((first_token_time - start_time) * 1000, 1) if first_token_time else None
            tps = round(token_count / ((time.time() - start_time) or 0.001), 1)

            metrics_tracker.record(
                PerformanceMetric(
                    provider=self.provider_id,
                    model=model,
                    mode="cloud",
                    latency_ms=total_ms,
                    time_to_first_token_ms=ttft_ms,
                    total_time_ms=total_ms,
                    token_count=token_count,
                    tokens_per_second=tps,
                    network_used=True,
                )
            )

        except Exception as e:
            sanitized = self._sanitize_error(e)
            yield f"\n[OpenAI Error: {sanitized}]"

    async def health_check(self) -> ProviderStatus:
        configured = self.is_configured()
        if not configured:
            return ProviderStatus(
                provider=self.provider_id,
                name=self.provider_name,
                type="cloud",
                available=False,
                configured=False,
                status_text="Not configured (missing OPENAI_API_KEY)",
                endpoint=self._base_url,
                active_model=self._default_model,
            )

        client = self._get_client()
        start = time.time()
        try:
            # Lightweight models query to verify auth & network
            await client.models.list()
            latency = round((time.time() - start) * 1000, 1)
            return ProviderStatus(
                provider=self.provider_id,
                name=self.provider_name,
                type="cloud",
                available=True,
                configured=True,
                status_text="Connected",
                models_count=len(self.get_models()),
                active_model=self._default_model,
                endpoint=self._base_url,
                latency_ms=latency,
            )
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return ProviderStatus(
                provider=self.provider_id,
                name=self.provider_name,
                type="cloud",
                available=False,
                configured=True,
                status_text=f"Authentication or Connection Failed",
                models_count=len(self.get_models()),
                active_model=self._default_model,
                endpoint=self._base_url,
                latency_ms=latency,
                error=sanitized,
            )

    def get_models(self) -> List[ModelInfo]:
        configured = self.is_configured()
        return [
            ModelInfo(
                id="openai:gpt-4o-mini",
                provider=self.provider_id,
                name="GPT-4o Mini",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                    ModelCapability.DOCUMENT.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Fast, high-efficiency cloud multimodal model.",
                context_length=128000,
            ),
            ModelInfo(
                id="openai:gpt-4o",
                provider=self.provider_id,
                name="GPT-4o",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                    ModelCapability.DOCUMENT.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Advanced multimodal intelligence model.",
                context_length=128000,
            ),
        ]

    def get_capabilities(self) -> List[str]:
        return [
            ModelCapability.TEXT.value,
            ModelCapability.VISION.value,
            ModelCapability.CODING.value,
            ModelCapability.REASONING.value,
            ModelCapability.STREAMING.value,
            ModelCapability.DOCUMENT.value,
        ]
