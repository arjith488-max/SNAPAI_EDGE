"""SnapAI Edge - Benchmarking API"""

import uuid
import time
import os
import psutil
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.db import get_db, BenchmarkResult
from ai.router import router as ai_router

router = APIRouter()

TEST_PROMPT = "Explain the concept of edge AI in exactly 3 sentences."


@router.post("/run")
async def run_benchmark(db: Session = Depends(get_db)):
    """Run a standardized benchmark comparing local vs cloud AI."""
    results = []

    # ─── Cloud benchmark ──────────────────────────────────
    if ai_router.jina_key or os.getenv("OPENAI_API_KEY"):
        start_mem = psutil.Process().memory_info().rss / 1e6
        start = time.time()
        try:
            result = await ai_router.chat(
                [{"role": "user", "content": TEST_PROMPT}],
                prefer_local=False,
            )
            latency = round((time.time() - start) * 1000, 1)
            end_mem = psutil.Process().memory_info().rss / 1e6

            br = BenchmarkResult(
                id=str(uuid.uuid4()),
                test_name="chat_cloud",
                model=result.get("model", "cloud"),
                mode="cloud",
                latency_ms=latency,
                memory_mb=round(end_mem - start_mem, 2),
                success="error" not in result,
                error=result.get("error"),
            )
            db.add(br)
            results.append({
                "mode": "cloud",
                "model": result.get("model"),
                "latency_ms": latency,
                "success": "error" not in result,
                "provider": result.get("provider"),
            })
        except Exception as e:
            results.append({"mode": "cloud", "error": str(e), "success": False})

    # ─── Local benchmark (Ollama) ─────────────────────────
    ollama_ok = await ai_router.is_ollama_available()
    if ollama_ok:
        start_mem = psutil.Process().memory_info().rss / 1e6
        start = time.time()
        try:
            result = await ai_router.chat_ollama(
                [{"role": "user", "content": TEST_PROMPT}]
            )
            latency = round((time.time() - start) * 1000, 1)
            end_mem = psutil.Process().memory_info().rss / 1e6

            br = BenchmarkResult(
                id=str(uuid.uuid4()),
                test_name="chat_local",
                model=result.get("model", "ollama"),
                mode="local",
                latency_ms=latency,
                memory_mb=round(end_mem - start_mem, 2),
                success="error" not in result,
                error=result.get("error"),
            )
            db.add(br)
            results.append({
                "mode": "local",
                "model": result.get("model"),
                "latency_ms": latency,
                "success": "error" not in result,
                "provider": "Ollama (Local)",
            })
        except Exception as e:
            results.append({"mode": "local", "error": str(e), "success": False})

    # ─── Embedding benchmark ──────────────────────────────
    if ai_router.jina_key:
        sample_texts = [
            "Snapdragon X Elite delivers on-device AI with its powerful NPU.",
            "Edge AI reduces latency and protects privacy by keeping data local.",
        ]
        start = time.time()
        try:
            embed_result = await ai_router.embed(sample_texts)
            latency = round((time.time() - start) * 1000, 1)
            br = BenchmarkResult(
                id=str(uuid.uuid4()),
                test_name="embed_jina",
                model=embed_result.get("model", "jina-embeddings-v3"),
                mode="cloud",
                latency_ms=latency,
                success="error" not in embed_result,
            )
            db.add(br)
            results.append({
                "mode": "cloud",
                "test": "embedding",
                "model": embed_result.get("model"),
                "latency_ms": latency,
                "texts": len(sample_texts),
                "success": "error" not in embed_result,
            })
        except Exception as e:
            results.append({"test": "embedding", "error": str(e), "success": False})

    db.commit()

    return {
        "results": results,
        "summary": {
            "tests_run": len(results),
            "tests_passed": sum(1 for r in results if r.get("success")),
            "fastest_mode": min(
                [r for r in results if r.get("latency_ms")],
                key=lambda x: x["latency_ms"],
                default={}
            ).get("mode", "N/A"),
        },
    }


@router.get("/results")
async def get_results(db: Session = Depends(get_db)):
    rows = db.query(BenchmarkResult).order_by(BenchmarkResult.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "test_name": r.test_name,
            "model": r.model,
            "mode": r.mode,
            "latency_ms": r.latency_ms,
            "memory_mb": r.memory_mb,
            "success": r.success,
            "error": r.error,
            "created_at": r.created_at,
        }
        for r in rows
    ]
