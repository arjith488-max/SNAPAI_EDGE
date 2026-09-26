"""SnapAI Edge - Hardware Detection API"""

import platform
import subprocess
import json
import os
import time
from fastapi import APIRouter

router = APIRouter()

_cached_info = None
_cache_time = 0


def detect_hardware() -> dict:
    info = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "cpu": {
            "brand": "Unknown",
            "architecture": platform.machine(),
            "cores_physical": None,
            "cores_logical": None,
            "frequency_mhz": None,
            "is_arm64": platform.machine().lower() in ("arm64", "aarch64"),
            "is_snapdragon": False,
        },
        "memory": {"total_gb": None, "available_gb": None, "percent_used": None},
        "disk": {"total_gb": None, "free_gb": None},
        "gpus": [],
        "acceleration": {
            "onnxruntime": False,
            "directml": False,
            "cuda": False,
            "npu_detected": False,
            "providers": [],
        },
        "network": {"connected": False},
        "ai_mode": "cloud_fallback",
        "snapdragon_ready": False,
    }

    # CPU via psutil
    try:
        import psutil
        info["cpu"]["cores_physical"] = psutil.cpu_count(logical=False)
        info["cpu"]["cores_logical"] = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        if freq:
            info["cpu"]["frequency_mhz"] = round(freq.current, 1)
        mem = psutil.virtual_memory()
        info["memory"]["total_gb"] = round(mem.total / 1e9, 2)
        info["memory"]["available_gb"] = round(mem.available / 1e9, 2)
        info["memory"]["percent_used"] = mem.percent
        disk = psutil.disk_usage("C:\\")
        info["disk"]["total_gb"] = round(disk.total / 1e9, 2)
        info["disk"]["free_gb"] = round(disk.free / 1e9, 2)
    except ImportError:
        pass

    # CPU brand via WMI
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_Processor | Select-Object -First 1 Name | ConvertTo-Json"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            info["cpu"]["brand"] = data.get("Name", "Unknown")
    except Exception:
        pass

    snapdragon_kw = ["snapdragon", "oryon", "kryo", "qualcomm"]
    brand = info["cpu"]["brand"].lower()
    info["cpu"]["is_snapdragon"] = any(k in brand for k in snapdragon_kw)
    info["cpu"]["is_arm64"] = info["cpu"]["is_arm64"] or "oryon" in brand

    # GPU via WMI
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            gpus = json.loads(r.stdout)
            if not isinstance(gpus, list):
                gpus = [gpus]
            for g in gpus:
                ram = g.get("AdapterRAM") or 0
                info["gpus"].append({
                    "name": g.get("Name", "Unknown"),
                    "vram_gb": round(ram / 1e9, 2) if ram > 0 else None,
                    "driver": g.get("DriverVersion"),
                    "is_qualcomm": "adreno" in g.get("Name", "").lower() or "qualcomm" in g.get("Name", "").lower(),
                })
    except Exception:
        pass

    # ONNX Runtime
    try:
        import onnxruntime as ort
        info["acceleration"]["onnxruntime"] = True
        info["acceleration"]["onnxruntime_version"] = ort.__version__
        providers = ort.get_available_providers()
        info["acceleration"]["providers"] = providers
        if "DmlExecutionProvider" in providers:
            info["acceleration"]["directml"] = True
        if "CUDAExecutionProvider" in providers:
            info["acceleration"]["cuda"] = True
    except ImportError:
        pass

    # Internet
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=4)
        info["network"]["connected"] = True
    except Exception:
        info["network"]["connected"] = False

    # Determine AI mode
    if info["cpu"]["is_snapdragon"] and info["acceleration"].get("directml"):
        info["ai_mode"] = "local_npu_primary"
        info["snapdragon_ready"] = True
    elif info["acceleration"].get("directml") or info["acceleration"].get("cuda"):
        info["ai_mode"] = "local_gpu_primary"
    elif info["cpu"]["is_arm64"]:
        info["ai_mode"] = "local_cpu_with_cloud_fallback"
    else:
        info["ai_mode"] = "cloud_fallback_primary"

    return info


@router.get("/info")
async def device_info():
    global _cached_info, _cache_time
    now = time.time()
    if _cached_info and (now - _cache_time) < 60:
        return _cached_info
    _cached_info = detect_hardware()
    _cache_time = now
    return _cached_info


@router.get("/quick")
async def device_quick():
    """Lightweight status — no subprocess calls."""
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": cpu_pct,
            "memory_percent": mem.percent,
            "memory_available_gb": round(mem.available / 1e9, 2),
        }
    except ImportError:
        return {"error": "psutil not available"}
