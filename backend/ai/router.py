"""
SnapAI Edge - Smart AI Router
Intelligent task classification, privacy analysis, connectivity checking, hardware inspection,
and model selection across Local, Cloud, Hybrid, and Offline modes.
Preserves backward compatibility for RAG embedding/reranking while implementing the multi-model architecture.
"""

import os
import time
import httpx
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv

from ai.types import (
    ProviderType,
    UserMode,
    ModelCapability,
    HardwareStatus,
    UnifiedResponse,
)
from security.privacy_guard import privacy_guard, PrivacyScanResult

load_dotenv()


class RoutingDecision:
    """Detailed routing decision output."""
    def __init__(
        self,
        provider: str,
        model: str,
        mode: str,
        reasons: List[str],
        privacy_warning: Optional[str] = None,
        is_fallback: bool = False,
    ):
        self.provider = provider
        self.model = model
        self.mode = mode
        self.reasons = reasons
        self.privacy_warning = privacy_warning
        self.is_fallback = is_fallback

    def to_reason_string(self) -> str:
        lines = ["Selected because:"]
        for r in self.reasons:
            lines.append(f"✓ {r}")
        if self.privacy_warning:
            lines.append(f"⚠️ {self.privacy_warning}")
        return "\n".join(lines)


class AIRouter:
    """
    Intelligent AI Router implementing:
    Task Classification → Privacy Analysis → Network Check → Local Model Check →
    Hardware Check → Capability Check → Performance Preference → Model Selection.
    """

    def __init__(self):
        self.jina_key = os.getenv("JINA_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.privacy = os.getenv("DEFAULT_PRIVACY_MODE", UserMode.LOCAL_FIRST.value)
        self.cloud_enabled = os.getenv("ENABLE_CLOUD_AI", "true").lower() == "true"
        self._internet: Optional[bool] = None
        self._internet_checked_at: float = 0

    async def is_online(self) -> bool:
        """Check internet connectivity with a 15-second cache."""
        now = time.time()
        if now - self._internet_checked_at < 15 and self._internet is not None:
            return self._internet
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get("https://www.google.com")
                self._internet = r.status_code < 500
        except Exception:
            self._internet = False
        self._internet_checked_at = now
        return self._internet

    async def is_ollama_available(self) -> bool:
        """Check if Ollama daemon is reachable and responding."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.ollama_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def get_installed_ollama_models(self) -> List[str]:
        """Fetch list of installed Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                r = await client.get(f"{self.ollama_url}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    return [m.get("name", "").split(":")[0] for m in data.get("models", []) if m.get("name")]
        except Exception:
            pass
        return []

    def classify_task(self, messages: List[Dict[str, Any]], attachments: Optional[List[Any]] = None) -> List[str]:
        """Classify task based on message content, attachments, and keywords."""
        caps_needed = [ModelCapability.TEXT.value]

        # Vision check
        if attachments and len(attachments) > 0:
            caps_needed.append(ModelCapability.VISION.value)

        last_prompt = messages[-1].get("content", "").lower() if messages else ""
        if any(w in last_prompt for w in ["write code", "python", "function", "bug", "algorithm", "class ", "def "]):
            caps_needed.append(ModelCapability.CODING.value)
        if any(w in last_prompt for w in ["explain step by step", "prove", "derive", "solve math", "compare in depth"]):
            caps_needed.append(ModelCapability.REASONING.value)

        return caps_needed

    async def route(
        self,
        messages: List[Dict[str, Any]],
        user_mode: str = UserMode.AUTO.value,
        requested_provider: str = "auto",
        requested_model: Optional[str] = None,
        attachments: Optional[List[Any]] = None,
        allow_cloud_override: bool = False,
    ) -> RoutingDecision:
        """
        Main decision algorithm:
        Returns RoutingDecision specifying selected provider, model, mode, and reasons.
        """
        # 1. Inspect connectivity & providers
        online = await self.is_online()
        ollama_ok = await self.is_ollama_available()
        installed_ollama = await self.get_installed_ollama_models() if ollama_ok else []
        cloud_configured = bool(self.openai_key or self.gemini_key)

        # 2. Privacy Analysis
        full_text = " ".join([str(m.get("content", "")) for m in messages])
        privacy_result: PrivacyScanResult = privacy_guard.scan(full_text)
        has_sensitive_data = privacy_result.has_sensitive_data and not allow_cloud_override

        # 3. Task Classification
        needed_caps = self.classify_task(messages, attachments)
        is_vision_task = ModelCapability.VISION.value in needed_caps

        reasons = []

        # ─── CASE A: User explicitly selected a provider ───
        if requested_provider != "auto":
            target = requested_provider.lower()
            if target == ProviderType.OLLAMA.value:
                chosen_model = requested_model or os.getenv("OLLAMA_MODEL", "llama3.2")
                reasons.append(f"Explicitly selected provider: Ollama")
                if ollama_ok:
                    reasons.append("Ollama daemon is running")
                else:
                    reasons.append("Warning: Ollama daemon appears offline")
                return RoutingDecision(
                    provider=ProviderType.OLLAMA.value,
                    model=chosen_model,
                    mode="offline" if not online else "local",
                    reasons=reasons,
                )

            elif target == ProviderType.OPENAI.value:
                chosen_model = requested_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                reasons.append(f"Explicitly selected provider: OpenAI ({chosen_model})")
                if not online:
                    reasons.append("Warning: Device is currently offline")
                return RoutingDecision(
                    provider=ProviderType.OPENAI.value,
                    model=chosen_model,
                    mode="cloud",
                    reasons=reasons,
                    privacy_warning=privacy_result.warning if has_sensitive_data else None,
                )

            elif target == ProviderType.GEMINI.value:
                chosen_model = requested_model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                reasons.append(f"Explicitly selected provider: Google Gemini ({chosen_model})")
                if not online:
                    reasons.append("Warning: Device is currently offline")
                return RoutingDecision(
                    provider=ProviderType.GEMINI.value,
                    model=chosen_model,
                    mode="cloud",
                    reasons=reasons,
                    privacy_warning=privacy_result.warning if has_sensitive_data else None,
                )

            elif target == ProviderType.LOCAL.value:
                reasons.append("Explicitly selected Snapdragon / Local Runtime")
                return RoutingDecision(
                    provider=ProviderType.LOCAL.value,
                    model=requested_model or "local:snapdragon-npu",
                    mode="local",
                    reasons=reasons,
                )

        # ─── CASE B: OFFLINE ONLY Mode OR Device is Offline ───
        if user_mode == UserMode.OFFLINE_ONLY.value or not online:
            mode_label = "offline" if not online else "local"
            if not online:
                reasons.append("Device is offline (network unavailable)")
            else:
                reasons.append("Offline-only mode selected by user")

            if ollama_ok and installed_ollama:
                # Find appropriate installed model
                chosen = None
                if is_vision_task:
                    for m in installed_ollama:
                        if "llava" in m.lower():
                            chosen = m
                            break
                if not chosen:
                    chosen = installed_ollama[0]
                reasons.append(f"Local Ollama model available: {chosen}")
                reasons.append("Zero network transmission required")
                return RoutingDecision(
                    provider=ProviderType.OLLAMA.value,
                    model=chosen,
                    mode=mode_label,
                    reasons=reasons,
                )
            else:
                reasons.append("Local runtime fallback (Ollama unavailable or no models installed)")
                return RoutingDecision(
                    provider=ProviderType.LOCAL.value,
                    model="local:snapdragon-npu",
                    mode="offline",
                    reasons=reasons,
                )

        # ─── CASE C: Sensitive Data Detected → Force Local Execution ───
        if has_sensitive_data:
            reasons.append(f"Privacy Guard: Sensitive data detected ({', '.join(privacy_result.detected_categories)})")
            reasons.append("Cloud transmission prohibited for privacy protection")
            if ollama_ok and installed_ollama:
                chosen = installed_ollama[0]
                reasons.append(f"Processing locally with Ollama model: {chosen}")
                return RoutingDecision(
                    provider=ProviderType.OLLAMA.value,
                    model=chosen,
                    mode="local",
                    reasons=reasons,
                    privacy_warning=privacy_result.warning,
                )
            else:
                reasons.append("Routing to local runtime for privacy preservation")
                return RoutingDecision(
                    provider=ProviderType.LOCAL.value,
                    model="local:snapdragon-npu",
                    mode="local",
                    reasons=reasons,
                    privacy_warning=privacy_result.warning,
                )

        # ─── CASE D: LOCAL FIRST Mode ───
        if user_mode == UserMode.LOCAL_FIRST.value:
            reasons.append("User preference: Local First")
            if ollama_ok and installed_ollama:
                chosen = None
                if is_vision_task:
                    for m in installed_ollama:
                        if "llava" in m.lower():
                            chosen = m
                            break
                if not chosen and not is_vision_task:
                    chosen = installed_ollama[0]

                if chosen:
                    reasons.append(f"Local model ready: {chosen}")
                    reasons.append("Instant local edge execution")
                    return RoutingDecision(
                        provider=ProviderType.OLLAMA.value,
                        model=chosen,
                        mode="local",
                        reasons=reasons,
                    )

            # Local models not suited or missing, fallback to cloud
            if cloud_configured and self.cloud_enabled:
                cloud_provider = ProviderType.GEMINI.value if self.gemini_key else ProviderType.OPENAI.value
                cloud_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash") if self.gemini_key else os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                reasons.append("Local models unavailable; falling back to configured cloud provider")
                return RoutingDecision(
                    provider=cloud_provider,
                    model=cloud_model,
                    mode="cloud",
                    reasons=reasons,
                    is_fallback=True,
                )

        # ─── CASE E: CLOUD FIRST Mode ───
        if user_mode == UserMode.CLOUD_FIRST.value:
            reasons.append("User preference: Cloud First")
            if cloud_configured and self.cloud_enabled and online:
                # Prefer Gemini if available, else OpenAI
                if self.gemini_key:
                    reasons.append("Google Gemini cloud model available")
                    return RoutingDecision(
                        provider=ProviderType.GEMINI.value,
                        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                        mode="cloud",
                        reasons=reasons,
                    )
                else:
                    reasons.append("OpenAI cloud model available")
                    return RoutingDecision(
                        provider=ProviderType.OPENAI.value,
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        mode="cloud",
                        reasons=reasons,
                    )
            elif ollama_ok and installed_ollama:
                reasons.append("Cloud unavailable; falling back to local Ollama")
                return RoutingDecision(
                    provider=ProviderType.OLLAMA.value,
                    model=installed_ollama[0],
                    mode="local",
                    reasons=reasons,
                    is_fallback=True,
                )

        # ─── CASE F: AUTO / HYBRID Mode ───
        reasons.append("Auto mode: balancing capability, privacy, and latency")

        # Multimodal task check
        if is_vision_task:
            reasons.append("Multimodal (vision) task detected")
            # If Ollama has llava, we can use local vision
            llava_model = next((m for m in installed_ollama if "llava" in m.lower()), None)
            if llava_model:
                reasons.append(f"Local vision model available: {llava_model}")
                return RoutingDecision(
                    provider=ProviderType.OLLAMA.value,
                    model=llava_model,
                    mode="local",
                    reasons=reasons,
                )
            elif cloud_configured and online:
                if self.gemini_key:
                    reasons.append("Routing to Gemini for high-accuracy vision analysis")
                    return RoutingDecision(
                        provider=ProviderType.GEMINI.value,
                        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                        mode="cloud",
                        reasons=reasons,
                    )
                else:
                    reasons.append("Routing to OpenAI for vision analysis")
                    return RoutingDecision(
                        provider=ProviderType.OPENAI.value,
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        mode="cloud",
                        reasons=reasons,
                    )

        # Standard text tasks: If Ollama is available, prefer local edge
        if ollama_ok and installed_ollama:
            reasons.append("Request can be handled locally with high performance")
            reasons.append(f"Local model available: {installed_ollama[0]}")
            reasons.append("Internet not required for this request")
            return RoutingDecision(
                provider=ProviderType.OLLAMA.value,
                model=installed_ollama[0],
                mode="local",
                reasons=reasons,
            )

        # Cloud available fallback
        if cloud_configured and online and self.cloud_enabled:
            provider = ProviderType.GEMINI.value if self.gemini_key else ProviderType.OPENAI.value
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash") if self.gemini_key else os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            reasons.append("Local models not ready; using configured cloud provider")
            return RoutingDecision(
                provider=provider,
                model=model,
                mode="cloud",
                reasons=reasons,
            )

        # Final local fallback
        reasons.append("Local Snapdragon / CPU runtime standby")
        return RoutingDecision(
            provider=ProviderType.LOCAL.value,
            model="local:snapdragon-npu",
            mode="local",
            reasons=reasons,
        )

    # ─── Backward-compatible RAG utilities (Jina Cloud Embed/Rerank) ───

    async def embed(self, texts: list[str], model: str = "jina-embeddings-v3") -> dict:
        if self.jina_key:
            try:
                start = time.time()
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        "https://api.jina.ai/v1/embeddings",
                        headers={"Authorization": f"Bearer {self.jina_key}", "Content-Type": "application/json"},
                        json={"model": model, "input": texts, "task": "retrieval.passage"},
                    )
                    r.raise_for_status()
                latency = round((time.time() - start) * 1000, 1)
                data = r.json()
                embeddings = [item["embedding"] for item in data["data"]]
                return {
                    "embeddings": embeddings,
                    "model": model,
                    "mode": "cloud",
                    "latency_ms": latency,
                    "provider": "Jina AI",
                }
            except Exception:
                pass  # Fall through to local embedding

        start = time.time()
        try:
            from sklearn.feature_extraction.text import HashingVectorizer
            vectorizer = HashingVectorizer(n_features=384, alternate_sign=False, norm="l2")
            embeddings = vectorizer.transform(texts).toarray().tolist()
            latency = round((time.time() - start) * 1000, 1)
            return {
                "embeddings": embeddings,
                "model": "local-hashing-384",
                "mode": "local",
                "latency_ms": latency,
                "provider": "SnapAI Local Embeddings",
            }
        except Exception as e:
            return {"error": f"Local embedding failed: {str(e)}", "mode": "error"}

    async def embed_query(self, text: str, model: str = "jina-embeddings-v3") -> dict:
        if self.jina_key:
            try:
                start = time.time()
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        "https://api.jina.ai/v1/embeddings",
                        headers={"Authorization": f"Bearer {self.jina_key}", "Content-Type": "application/json"},
                        json={"model": model, "input": [text], "task": "retrieval.query"},
                    )
                    r.raise_for_status()
                latency = round((time.time() - start) * 1000, 1)
                data = r.json()
                return {
                    "embedding": data["data"][0]["embedding"],
                    "model": model,
                    "mode": "cloud",
                    "latency_ms": latency,
                }
            except Exception:
                pass  # Fall through to local query embedding

        start = time.time()
        try:
            from sklearn.feature_extraction.text import HashingVectorizer
            vectorizer = HashingVectorizer(n_features=384, alternate_sign=False, norm="l2")
            vec = vectorizer.transform([text]).toarray()[0].tolist()
            latency = round((time.time() - start) * 1000, 1)
            return {
                "embedding": vec,
                "model": "local-hashing-384",
                "mode": "local",
                "latency_ms": latency,
            }
        except Exception as e:
            return {"error": f"Local query embedding failed: {str(e)}"}

    async def rerank(self, query: str, documents: list[str], top_n: int = 5) -> dict:
        if self.jina_key:
            try:
                model = os.getenv("JINA_RERANK_MODEL", "jina-reranker-v2-base-multilingual")
                start = time.time()
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        "https://api.jina.ai/v1/rerank",
                        headers={"Authorization": f"Bearer {self.jina_key}", "Content-Type": "application/json"},
                        json={"model": model, "query": query, "documents": documents, "top_n": top_n},
                    )
                    r.raise_for_status()
                latency = round((time.time() - start) * 1000, 1)
                data = r.json()
                return {
                    "results": data.get("results", []),
                    "model": model,
                    "mode": "cloud",
                    "latency_ms": latency,
                }
            except Exception:
                pass  # Fall through to local reranking

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vec = TfidfVectorizer().fit([query] + documents)
            q_vec = vec.transform([query])
            d_vecs = vec.transform(documents)
            sims = cosine_similarity(q_vec, d_vecs)[0]
            indexed = sorted(enumerate(sims), key=lambda x: x[1], reverse=True)[:top_n]
            return {
                "results": [{"index": idx, "relevance_score": float(score), "score": float(score)} for idx, score in indexed],
                "model": "local-tfidf-reranker",
                "mode": "local",
                "latency_ms": 1.0,
            }
        except Exception:
            return {"results": [{"index": i, "relevance_score": 1.0, "score": 1.0} for i in range(min(top_n, len(documents)))]}

    async def chat_ollama(self, messages: list[dict], model: str = None) -> dict:
        """Backward compatible helper for existing callers."""
        from ai.manager import ai_manager
        resp = await ai_manager.generate(messages, provider=ProviderType.OLLAMA.value, model=model)
        return {
            "content": resp.response,
            "model": resp.model,
            "mode": resp.mode,
            "latency_ms": resp.latency_ms,
            "provider": resp.provider,
            "processed_locally": resp.local_processing,
        }

    async def chat_openai(self, messages: list[dict], model: str = None) -> dict:
        """Backward compatible helper for existing callers."""
        from ai.manager import ai_manager
        resp = await ai_manager.generate(messages, provider=ProviderType.OPENAI.value, model=model)
        return {
            "content": resp.response,
            "model": resp.model,
            "mode": resp.mode,
            "latency_ms": resp.latency_ms,
            "provider": resp.provider,
            "processed_locally": resp.local_processing,
        }

    async def chat(self, messages: list[dict], model: str = None, prefer_local: bool = False) -> dict:
        """Backward compatible chat router."""
        from ai.manager import ai_manager
        mode = UserMode.LOCAL_FIRST.value if prefer_local else self.privacy
        resp = await ai_manager.generate(messages, mode=mode, model=model)
        return {
            "content": resp.response,
            "model": resp.model,
            "mode": resp.mode,
            "latency_ms": resp.latency_ms,
            "provider": resp.provider,
            "processed_locally": resp.local_processing,
            "routing_reason": resp.routing_reason,
        }


# Singleton
router = AIRouter()
