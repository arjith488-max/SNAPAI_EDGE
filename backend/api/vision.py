"""SnapAI Edge - Vision API (image analysis, OCR, VQA)"""

import base64
import io
import os
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional

from ai.router import router as ai_router

router = APIRouter()
MAX_IMAGE_MB = 10


def image_to_base64(data: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(data).decode()
    return f"data:{mime}:{b64}"


def compress_image(data: bytes, max_pixels: int = 1024) -> tuple[bytes, str]:
    """Resize image to max dimension and return compressed JPEG bytes."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_pixels:
            ratio = max_pixels / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "image/jpeg"
    except ImportError:
        return data, "image/jpeg"


async def analyze_image_with_ollama(image_b64: str, prompt: str) -> dict:
    """Try vision-capable Ollama model (llava)."""
    import httpx
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = "llava"
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64.split(",")[-1]],
                    "stream": False,
                },
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "content": data.get("response", ""),
                    "mode": "local",
                    "model": model,
                    "latency_ms": round((time.time() - start) * 1000, 1),
                    "processed_locally": True,
                }
    except Exception:
        pass
    return {"error": "Ollama vision unavailable"}


async def analyze_image_with_openai(image_b64: str, prompt: str) -> dict:
    """Fallback: OpenAI GPT-4o vision."""
    import httpx
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return {"error": "No OpenAI API key"}
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    start = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_b64}},
                        ],
                    }
                ],
            },
        )
        r.raise_for_status()
    data = r.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "mode": "cloud",
        "model": model,
        "latency_ms": round((time.time() - start) * 1000, 1),
        "processed_locally": False,
        "provider": "OpenAI Vision",
    }


def run_ocr(data: bytes) -> str:
    """Extract text from image using available OCR."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        # Try pytesseract
        try:
            import pytesseract
            return pytesseract.image_to_string(img)
        except ImportError:
            pass
        # Try EasyOCR
        try:
            import easyocr
            reader = easyocr.Reader(["en"], gpu=False)
            result = reader.readtext(data, detail=0)
            return "\n".join(result)
        except ImportError:
            pass
        return "[OCR unavailable: install pytesseract or easyocr]"
    except Exception as e:
        return f"[OCR failed: {str(e)}]"


@router.post("/vision")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form(default="Describe this image in detail."),
    task: str = Form(default="describe"),  # describe|ocr|vqa|diagram|chart|compare
    prefer_local: bool = Form(default=False),
):
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_IMAGE_MB:
        raise HTTPException(400, f"Image too large ({size_mb:.1f} MB). Max: {MAX_IMAGE_MB} MB.")

    mime = file.content_type or "image/jpeg"
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(400, f"Unsupported image type: {mime}")

    # Compress
    compressed, mime = compress_image(content)

    # OCR task
    if task == "ocr":
        text = run_ocr(compressed)
        return {
            "task": "ocr",
            "text": text,
            "mode": "local",
            "processed_locally": True,
            "model": "OCR Engine",
        }

    # Build prompt based on task
    task_prompts = {
        "describe":   "Describe this image in detail, including all visible objects, text, colors, and context.",
        "diagram":    "Explain this diagram step by step. Identify all components and their relationships.",
        "chart":      "Analyze this chart/graph. Identify the type, axes, key values, trends, and what conclusions can be drawn.",
        "objects":    "Identify and list all major objects visible in this image with their approximate locations.",
        "summarize":  "Provide a concise summary of what this image shows and its key information.",
        "code":       "Extract and explain any code, equations, or technical content visible in this image.",
    }
    effective_prompt = prompt if task == "vqa" else task_prompts.get(task, prompt)

    # Convert to base64
    b64 = image_to_base64(compressed, mime)

    # Try local first
    if prefer_local:
        result = await analyze_image_with_ollama(b64, effective_prompt)
        if "error" not in result:
            return {"task": task, **result}

    # Try OpenAI vision
    result = await analyze_image_with_openai(b64, effective_prompt)
    if "error" not in result:
        return {"task": task, **result}

    # Try Ollama as last resort
    result = await analyze_image_with_ollama(b64, effective_prompt)
    if "error" not in result:
        return {"task": task, **result}

    return {
        "task": task,
        "content": "⚠️ Vision AI unavailable. Please configure OpenAI API key or install Ollama with 'llava' model.",
        "mode": "error",
        "error": result.get("error"),
    }
