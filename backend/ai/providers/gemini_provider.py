"""
SnapAI Edge - Google Gemini Provider
Integration using the Google Gemini SDK with streaming, multimodal input, error sanitization, and latency capture.
Never exposes API keys in logs or responses.
"""

import os
import time
import io
import base64
from typing import AsyncGenerator, List, Dict, Any, Optional
from dotenv import load_dotenv

from ai.base import AIProvider
from ai.types import UnifiedResponse, ModelInfo, ProviderStatus, ProviderType, ModelCapability
from ai.metrics import metrics_tracker, PerformanceMetric

load_dotenv()

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import google.generativeai as genai
    from google.api_core.exceptions import (
        GoogleAPIError,
        PermissionDenied,
        ResourceExhausted,
        InvalidArgument,
        ServiceUnavailable,
    )
except ImportError:
    genai = None
    GoogleAPIError = Exception
    PermissionDenied = Exception
    ResourceExhausted = Exception
    InvalidArgument = Exception
    ServiceUnavailable = Exception


class GeminiProvider(AIProvider):
    """
    Google Gemini Cloud Provider implementation.
    """

    def __init__(self):
        self._api_key = self._resolve_api_key()
        self._default_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        self._configured = False
        self._init_sdk()

    def _resolve_api_key(self) -> str:
        # Check current os.environ first (respects runtime overrides and tests)
        if "GEMINI_API_KEY" in os.environ:
            return os.environ["GEMINI_API_KEY"].strip()
        if "GOOGLE_API_KEY" in os.environ:
            return os.environ["GOOGLE_API_KEY"].strip()
        load_dotenv()
        return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

    def _init_sdk(self):
        self._api_key = self._resolve_api_key()
        if self._api_key and genai is not None:
            try:
                genai.configure(api_key=self._api_key)
                self._configured = True
            except Exception:
                self._configured = False
        else:
            self._configured = False

    @property
    def provider_id(self) -> str:
        return ProviderType.GEMINI.value

    @property
    def provider_name(self) -> str:
        return "Google Gemini"

    @property
    def is_local(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return bool(self._resolve_api_key())

    def _sanitize_error(self, err: Exception) -> str:
        msg = str(err)
        keys_to_check = [
            getattr(self, "_api_key", ""),
            self._resolve_api_key(),
            os.environ.get("GEMINI_API_KEY", ""),
            os.environ.get("GOOGLE_API_KEY", ""),
        ]
        for k in keys_to_check:
            if k and len(k) > 5:
                msg = msg.replace(k, "[REDACTED_API_KEY]")
        return msg

    def _prepare_contents(self, messages: List[Dict[str, Any]], model_name: str) -> List[Any]:
        """
        Convert standard chat messages format to Gemini format.
        Supports multimodal attachments (images) for models that support vision.
        """
        contents = []
        is_vision = "flash" in model_name.lower() or "pro" in model_name.lower()

        for m in messages:
            role = m.get("role", "user")
            gemini_role = "user" if role in ("user", "system") else "model"
            content = m.get("content", "")
            attachments = m.get("attachments", [])

            parts = []
            if content:
                parts.append(str(content))

            # Handle image attachments
            if attachments and is_vision:
                for att in attachments:
                    data = None
                    mime = "image/jpeg"
                    if isinstance(att, dict):
                        url = att.get("url", "")
                        mime = att.get("mime", "image/jpeg")
                        if url.startswith("data:image"):
                            try:
                                header, encoded = url.split(",", 1)
                                if "image/" in header:
                                    mime = header.split(";")[0].split(":")[1]
                                data = base64.b64decode(encoded)
                            except Exception:
                                pass
                    elif isinstance(att, str) and att.startswith("data:image"):
                        try:
                            header, encoded = att.split(",", 1)
                            if "image/" in header:
                                mime = header.split(";")[0].split(":")[1]
                            data = base64.b64decode(encoded)
                        except Exception:
                            pass

                    if data:
                        parts.append({"mime_type": mime, "data": data})

            if parts:
                contents.append({"role": gemini_role, "parts": parts})

        return contents

    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> UnifiedResponse:
        self._init_sdk()
        if not self._configured or not self._api_key:
            return UnifiedResponse(
                provider=self.provider_id,
                model=kwargs.get("model", self._default_model),
                mode="cloud",
                response="Google Gemini API key is not configured. Please add GEMINI_API_KEY in your settings or .env file.",
                latency_ms=0.0,
                streaming=False,
                network_used=False,
                local_processing=False,
                routing_reason="Gemini unconfigured",
                metadata={"error": "GEMINI_API_KEY missing"},
            )

        model_name = kwargs.get("model") or self._default_model
        # Strip provider prefix if present (e.g. "gemini:gemini-1.5-flash" -> "gemini-1.5-flash")
        if ":" in model_name:
            model_name = model_name.split(":", 1)[1]

        contents = self._prepare_contents(messages, model_name)
        start_time = time.time()

        try:
            model = genai.GenerativeModel(model_name)
            resp = await model.generate_content_async(contents)
            latency_ms = round((time.time() - start_time) * 1000, 1)

            text_output = ""
            if resp and resp.text:
                text_output = resp.text

            usage = {}
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                usage = {
                    "prompt_token_count": getattr(resp.usage_metadata, "prompt_token_count", None),
                    "candidates_token_count": getattr(resp.usage_metadata, "candidates_token_count", None),
                    "total_token_count": getattr(resp.usage_metadata, "total_token_count", None),
                }

            metrics_tracker.record(
                PerformanceMetric(
                    provider=self.provider_id,
                    model=model_name,
                    mode="cloud",
                    latency_ms=latency_ms,
                    token_count=usage.get("candidates_token_count"),
                    network_used=True,
                    metadata=usage,
                )
            )

            return UnifiedResponse(
                provider=self.provider_id,
                model=model_name,
                mode="cloud",
                response=text_output,
                latency_ms=latency_ms,
                streaming=False,
                network_used=True,
                local_processing=False,
                routing_reason=kwargs.get("routing_reason"),
                metadata=usage,
            )

        except PermissionDenied as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model_name,
                mode="cloud",
                response=f"Gemini Permission Denied / Invalid Key: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "permission_denied", "details": sanitized},
            )
        except ResourceExhausted as e:
            # If preview model daily free limit is hit, attempt fallback to gemini-flash-lite-latest
            fallback_model = "gemini-flash-lite-latest"
            if model_name != fallback_model:
                try:
                    alt_model = genai.GenerativeModel(fallback_model)
                    resp = await alt_model.generate_content_async(contents)
                    if resp and resp.text:
                        latency_ms = round((time.time() - start_time) * 1000, 1)
                        return UnifiedResponse(
                            provider=self.provider_id,
                            model=fallback_model,
                            mode="cloud",
                            response=resp.text,
                            latency_ms=latency_ms,
                            streaming=False,
                            network_used=True,
                            local_processing=False,
                            routing_reason=f"Fell back from {model_name} (daily quota limit) to {fallback_model}",
                            metadata={"fallback_from": model_name},
                        )
                except Exception:
                    pass

            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model_name,
                mode="cloud",
                response=f"Gemini Quota Exceeded: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "quota_exceeded", "details": sanitized},
            )
        except ServiceUnavailable as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model_name,
                mode="cloud",
                response=f"Gemini Service Unavailable: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "service_unavailable", "details": sanitized},
            )
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            sanitized = self._sanitize_error(e)
            return UnifiedResponse(
                provider=self.provider_id,
                model=model_name,
                mode="cloud",
                response=f"Gemini Error: {sanitized}",
                latency_ms=latency_ms,
                network_used=True,
                local_processing=False,
                metadata={"error": "gemini_error", "details": sanitized},
            )

    async def stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        self._init_sdk()
        if not self._configured or not self._api_key:
            yield "Google Gemini API key is not configured. Please add GEMINI_API_KEY in your settings."
            return

        model_name = kwargs.get("model") or self._default_model
        if ":" in model_name:
            model_name = model_name.split(":", 1)[1]

        contents = self._prepare_contents(messages, model_name)
        start_time = time.time()
        first_token_time = None
        token_count = 0

        try:
            model = genai.GenerativeModel(model_name)
            response_stream = await model.generate_content_async(contents, stream=True)
            async for chunk in response_stream:
                if chunk and chunk.text:
                    if first_token_time is None:
                        first_token_time = time.time()
                    token_count += 1
                    yield chunk.text

            total_ms = round((time.time() - start_time) * 1000, 1)
            ttft_ms = round((first_token_time - start_time) * 1000, 1) if first_token_time else None
            tps = round(token_count / ((time.time() - start_time) or 0.001), 1)

            metrics_tracker.record(
                PerformanceMetric(
                    provider=self.provider_id,
                    model=model_name,
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
            fallback_model = "gemini-flash-lite-latest"
            if "quota" in str(e).lower() and model_name != fallback_model:
                try:
                    alt_model = genai.GenerativeModel(fallback_model)
                    alt_stream = await alt_model.generate_content_async(contents, stream=True)
                    async for chunk in alt_stream:
                        if chunk and chunk.text:
                            yield chunk.text
                    return
                except Exception:
                    pass
            sanitized = self._sanitize_error(e)
            yield f"\n[Gemini Error: {sanitized}]"

    async def health_check(self) -> ProviderStatus:
        self._init_sdk()
        if not self._api_key:
            return ProviderStatus(
                provider=self.provider_id,
                name=self.provider_name,
                type="cloud",
                available=False,
                configured=False,
                status_text="Not configured (missing GEMINI_API_KEY)",
                endpoint="googleapis.com",
                active_model=self._default_model,
            )

        start = time.time()
        try:
            # Quick check by querying models
            models_list = list(genai.list_models())
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
                endpoint="googleapis.com",
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
                status_text="Authentication or Connection Failed",
                models_count=len(self.get_models()),
                active_model=self._default_model,
                endpoint="googleapis.com",
                latency_ms=latency,
                error=sanitized,
            )

    def get_models(self) -> List[ModelInfo]:
        configured = self.is_configured()
        return [
            ModelInfo(
                id="gemini:gemini-flash-lite-latest",
                provider=self.provider_id,
                name="Gemini Flash Lite",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.AUDIO.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Ultra-fast, high-availability lightweight multimodal model from Google.",
                context_length=1000000,
            ),
            ModelInfo(
                id="gemini:gemini-1.5-flash",
                provider=self.provider_id,
                name="Gemini 1.5 Flash",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.AUDIO.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                    ModelCapability.DOCUMENT.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Fast and versatile multimodal model with 1M token context.",
                context_length=1000000,
            ),
            ModelInfo(
                id="gemini:gemini-1.5-pro",
                provider=self.provider_id,
                name="Gemini 1.5 Pro",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.AUDIO.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                    ModelCapability.DOCUMENT.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Complex reasoning multimodal model with 2M token context.",
                context_length=2000000,
            ),
            ModelInfo(
                id="gemini:gemini-2.0-flash",
                provider=self.provider_id,
                name="Gemini 2.0 Flash",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Next-generation high-speed multimodal reasoning model.",
                context_length=1000000,
            ),
            ModelInfo(
                id="gemini:gemini-3.8-flash",
                provider=self.provider_id,
                name="Gemini 3.8 Flash",
                location="cloud",
                capabilities=[
                    ModelCapability.TEXT.value,
                    ModelCapability.VISION.value,
                    ModelCapability.CODING.value,
                    ModelCapability.REASONING.value,
                    ModelCapability.STREAMING.value,
                ],
                streaming=True,
                vision=True,
                embedding=False,
                available=configured,
                description="Ultra-fast flagship multimodal model from Google.",
                context_length=1000000,
            ),
        ]

    def get_capabilities(self) -> List[str]:
        return [
            ModelCapability.TEXT.value,
            ModelCapability.VISION.value,
            ModelCapability.AUDIO.value,
            ModelCapability.CODING.value,
            ModelCapability.REASONING.value,
            ModelCapability.STREAMING.value,
            ModelCapability.DOCUMENT.value,
        ]
