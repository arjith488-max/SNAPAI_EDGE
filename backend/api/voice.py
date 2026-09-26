"""SnapAI Edge - Voice / Speech API"""

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from ai.router import router as ai_router

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """Transcribe audio using Whisper (via Ollama) or OpenAI Whisper API."""
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > 25:
        raise HTTPException(400, "Audio file too large (max 25 MB).")

    mime = file.content_type or ""
    allowed_audio = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/webm",
                     "audio/ogg", "audio/flac", "audio/mp4", "audio/m4a"]
    if mime not in allowed_audio:
        raise HTTPException(400, f"Unsupported audio format: {mime}")

    # Try OpenAI Whisper API
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            import httpx
            import time
            start = time.time()
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    files={"file": (file.filename, content, mime)},
                    data={"model": "whisper-1", "language": language},
                )
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "text": data.get("text", ""),
                        "language": language,
                        "mode": "cloud",
                        "model": "whisper-1",
                        "latency_ms": round((time.time() - start) * 1000, 1),
                        "processed_locally": False,
                    }
        except Exception as e:
            pass  # Fall through to local

    # Try local Whisper via faster-whisper
    try:
        from faster_whisper import WhisperModel
        import time
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            start = time.time()
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, info = model.transcribe(tmp_path, language=language)
            text = " ".join(s.text for s in segments)
            return {
                "text": text.strip(),
                "language": info.language,
                "mode": "local",
                "model": "whisper-tiny",
                "latency_ms": round((time.time() - start) * 1000, 1),
                "processed_locally": True,
            }
        finally:
            os.unlink(tmp_path)
    except ImportError:
        pass
    except Exception as e:
        pass

    return {
        "text": "",
        "error": "Speech recognition unavailable. Install faster-whisper for local mode or configure OpenAI API key for cloud transcription.",
        "mode": "error",
    }


class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy"
    language: str = "en"


@router.post("/speak")
async def text_to_speech(req: TTSRequest):
    """Convert text to speech. Returns status - actual TTS done client-side via Web Speech API."""
    # Web Speech API handles TTS in the browser natively.
    # This endpoint can be extended with ElevenLabs/OpenAI TTS when configured.
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key and len(req.text) < 4096:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')}/audio/speech",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={"model": "tts-1", "input": req.text, "voice": req.voice},
                )
                if r.status_code == 200:
                    from fastapi.responses import Response
                    return Response(content=r.content, media_type="audio/mpeg")
        except Exception:
            pass

    return {
        "status": "use_browser_tts",
        "message": "Use Web Speech API for TTS, or configure OpenAI API key for cloud TTS.",
        "text": req.text,
    }
