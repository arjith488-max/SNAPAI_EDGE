"""
SnapAI Edge - Hardware Compatibility Report Generator
Detects CPU, GPU, memory, architecture, and AI acceleration capabilities.
"""

import json
import sys
import os
import platform
import subprocess
import shutil
from datetime import datetime

def get_cpu_info():
    info = {
        "brand": "Unknown",
        "architecture": platform.machine(),
        "cores_physical": None,
        "cores_logical": None,
        "frequency_mhz": None,
        "is_arm64": False,
        "is_snapdragon": False,
    }
    info["is_arm64"] = platform.machine().lower() in ("arm64", "aarch64")

    try:
        import cpuinfo
        cpu = cpuinfo.get_cpu_info()
        info["brand"] = cpu.get("brand_raw", "Unknown")
        info["architecture"] = cpu.get("arch", platform.machine())
        info["is_arm64"] = "arm" in info["architecture"].lower() or "aarch" in info["architecture"].lower()
    except ImportError:
        # Fallback: use platform/WMI on Windows
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    data = data[0]
                info["brand"] = data.get("Name", "Unknown")
                info["cores_physical"] = data.get("NumberOfCores")
                info["cores_logical"] = data.get("NumberOfLogicalProcessors")
                info["frequency_mhz"] = data.get("MaxClockSpeed")
        except Exception as e:
            info["brand_detect_error"] = str(e)

    try:
        import psutil
        info["cores_physical"] = psutil.cpu_count(logical=False)
        info["cores_logical"] = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        if freq:
            info["frequency_mhz"] = round(freq.max, 1)
    except ImportError:
        pass

    snapdragon_keywords = ["snapdragon", "oryon", "kryo", "qualcomm"]
    brand_lower = info["brand"].lower()
    info["is_snapdragon"] = any(k in brand_lower for k in snapdragon_keywords)

    return info


def get_memory_info():
    info = {"total_gb": None, "available_gb": None, "percent_used": None}
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["total_gb"] = round(mem.total / (1024 ** 3), 2)
        info["available_gb"] = round(mem.available / (1024 ** 3), 2)
        info["percent_used"] = mem.percent
    except ImportError:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                total = data.get("TotalPhysicalMemory", 0)
                info["total_gb"] = round(total / (1024 ** 3), 2)
        except Exception as e:
            info["detect_error"] = str(e)
    return info


def get_disk_info():
    info = {"total_gb": None, "free_gb": None}
    try:
        import psutil
        disk = psutil.disk_usage("C:\\")
        info["total_gb"] = round(disk.total / (1024 ** 3), 2)
        info["free_gb"] = round(disk.free / (1024 ** 3), 2)
    except ImportError:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-PSDrive C | Select-Object Used,Free | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                used_bytes = data.get("Used", 0)
                free_bytes = data.get("Free", 0)
                total_bytes = used_bytes + free_bytes
                info["total_gb"] = round(total_bytes / (1024 ** 3), 2)
                info["free_gb"] = round(free_bytes / (1024 ** 3), 2)
        except Exception as e:
            info["detect_error"] = str(e)
    return info


def get_gpu_info():
    gpus = []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                data = [data]
            for gpu in data:
                ram = gpu.get("AdapterRAM")
                ram_gb = round(ram / (1024 ** 3), 2) if ram and ram > 0 else None
                gpus.append({
                    "name": gpu.get("Name", "Unknown"),
                    "vram_gb": ram_gb,
                    "driver_version": gpu.get("DriverVersion"),
                })
    except Exception as e:
        gpus.append({"detect_error": str(e)})

    # Check for Qualcomm Adreno GPU
    for gpu in gpus:
        name_lower = gpu.get("name", "").lower()
        gpu["is_adreno"] = "adreno" in name_lower
        gpu["is_qualcomm"] = "qualcomm" in name_lower or "adreno" in name_lower

    return gpus


def get_ai_acceleration():
    acceleration = {
        "directml": False,
        "onnxruntime": False,
        "onnxruntime_directml": False,
        "onnxruntime_cuda": False,
        "cuda": False,
        "rocm": False,
        "npu_available": False,
        "qualcomm_ai_engine": False,
        "notes": []
    }

    try:
        import onnxruntime as ort
        acceleration["onnxruntime"] = True
        providers = ort.get_available_providers()
        acceleration["onnxruntime_providers"] = providers
        if "DmlExecutionProvider" in providers:
            acceleration["directml"] = True
            acceleration["onnxruntime_directml"] = True
        if "CUDAExecutionProvider" in providers:
            acceleration["cuda"] = True
            acceleration["onnxruntime_cuda"] = True
        acceleration["notes"].append(f"ONNX Runtime {ort.__version__} available")
    except ImportError:
        acceleration["notes"].append("ONNX Runtime not installed")

    try:
        import torch
        acceleration["pytorch"] = True
        acceleration["pytorch_version"] = torch.__version__
        if torch.cuda.is_available():
            acceleration["cuda"] = True
            acceleration["notes"].append(f"CUDA available: {torch.cuda.get_device_name(0)}")
    except ImportError:
        acceleration["notes"].append("PyTorch not installed")

    # Check for NPU via WMI
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_PnPEntity | Where-Object {$_.Name -like '*NPU*' -or $_.Name -like '*neural*' -or $_.Name -like '*Hexagon*'} | Select-Object Name | ConvertTo-Json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "null":
            acceleration["npu_available"] = True
            acceleration["notes"].append(f"NPU device detected: {result.stdout.strip()[:200]}")
    except Exception:
        pass

    # Check DirectML availability
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-WindowsCapability -Online | Where-Object Name -like '*DirectML*'"],
            capture_output=True, text=True, timeout=10
        )
        if "Installed" in result.stdout:
            acceleration["directml"] = True
    except Exception:
        pass

    return acceleration


def check_python_packages():
    required = [
        "fastapi", "uvicorn", "sqlalchemy", "pydantic",
        "pymupdf", "pytesseract", "pillow", "numpy",
        "sentence_transformers", "chromadb", "openai",
        "psutil", "httpx", "python-multipart"
    ]
    status = {}
    for pkg in required:
        try:
            mod_name = pkg.replace("-", "_")
            __import__(mod_name)
            status[pkg] = "installed"
        except ImportError:
            status[pkg] = "not_installed"
    return status


def check_internet():
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False


def main():
    print("=" * 60)
    print("  SnapAI Edge - Hardware Compatibility Report")
    print("=" * 60)

    report = {
        "generated_at": datetime.now().isoformat(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "gpus": get_gpu_info(),
        "ai_acceleration": get_ai_acceleration(),
        "python_packages": check_python_packages(),
        "internet_connected": check_internet(),
        "node_version": shutil.which("node") is not None,
    }

    # Node version
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        report["node_version"] = result.stdout.strip()
    except Exception:
        report["node_version"] = "not_found"

    # Summary
    cpu = report["cpu"]
    report["summary"] = {
        "is_snapdragon": cpu.get("is_snapdragon", False),
        "is_arm64": cpu.get("is_arm64", False),
        "has_npu": report["ai_acceleration"].get("npu_available", False),
        "has_directml": report["ai_acceleration"].get("directml", False),
        "has_cuda": report["ai_acceleration"].get("cuda", False),
        "has_onnxruntime": report["ai_acceleration"].get("onnxruntime", False),
        "internet_connected": report["internet_connected"],
        "recommended_mode": "cloud_fallback_primary"
    }

    s = report["summary"]
    if s["is_snapdragon"] and s["has_npu"]:
        s["recommended_mode"] = "local_npu_primary"
    elif s["has_directml"] or s["has_cuda"]:
        s["recommended_mode"] = "local_gpu_primary"
    elif s["is_arm64"]:
        s["recommended_mode"] = "local_cpu_with_cloud_fallback"

    # Save report
    out_path = os.path.join(os.path.dirname(__file__), "..", "hardware_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report["summary"], indent=2))
    print(f"\nFull report saved to: hardware_report.json")
    return report


if __name__ == "__main__":
    main()
