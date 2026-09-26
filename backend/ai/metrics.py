"""
SnapAI Edge - Performance Metrics Tracker
Captures and records genuine inference metrics: latency, TTFT, tokens/sec, memory/CPU usage.
Never fabricates metrics. If a metric is unmeasured, it remains None or N/A.
"""

import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

try:
    import psutil
except ImportError:
    psutil = None


class PerformanceMetric(BaseModel):
    provider: str
    model: str
    mode: str
    latency_ms: float
    time_to_first_token_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    token_count: Optional[int] = None
    tokens_per_second: Optional[float] = None
    memory_used_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    gpu_usage: Optional[float] = None
    npu_usage: Optional[float] = None
    network_used: bool = False
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsTracker:
    """
    In-memory and persistent tracker for AI inference metrics.
    """

    def __init__(self, max_history: int = 200):
        self._history: List[PerformanceMetric] = []
        self._max_history = max_history

    @staticmethod
    def get_system_snapshot() -> Dict[str, Any]:
        """Measure current real CPU and memory usage if psutil is available."""
        snapshot = {}
        if psutil:
            try:
                proc = psutil.Process()
                mem = proc.memory_info()
                snapshot["process_rss_mb"] = round(mem.rss / (1024 * 1024), 2)
                snapshot["system_cpu_percent"] = psutil.cpu_percent(interval=None)
                snapshot["system_memory_percent"] = psutil.virtual_memory().percent
            except Exception:
                pass
        return snapshot

    def record(self, metric: PerformanceMetric) -> PerformanceMetric:
        """Store measured metric in history."""
        self._history.append(metric)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        return metric

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent metrics."""
        return [m.model_dump() for m in reversed(self._history[-limit:])]

    def get_summary_by_provider(self) -> Dict[str, Any]:
        """Aggregate real measured latency by provider."""
        summary: Dict[str, Dict[str, Any]] = {}
        for m in self._history:
            p = m.provider
            if p not in summary:
                summary[p] = {"count": 0, "total_latency": 0.0, "min_latency": float("inf"), "max_latency": 0.0}
            summary[p]["count"] += 1
            summary[p]["total_latency"] += m.latency_ms
            summary[p]["min_latency"] = min(summary[p]["min_latency"], m.latency_ms)
            summary[p]["max_latency"] = max(summary[p]["max_latency"], m.latency_ms)

        for p, data in summary.items():
            if data["count"] > 0:
                data["avg_latency_ms"] = round(data["total_latency"] / data["count"], 2)
                data["min_latency_ms"] = round(data["min_latency"], 2)
                data["max_latency_ms"] = round(data["max_latency"], 2)
                del data["total_latency"]
                del data["min_latency"]
                del data["max_latency"]

        return summary


# Global metrics tracker
metrics_tracker = MetricsTracker()
