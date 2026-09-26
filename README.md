# SnapAI Edge ⚡

> **One Interface → Multiple AI Models → Intelligent Model Selection → Local / Cloud / Hybrid / Offline Operation → Measurable Performance**
>
> Built for the **Qualcomm Snapdragon AI Lab Build & Present Challenge**

![SnapAI Edge](https://img.shields.io/badge/SnapAI%20Edge-v2.0-6366f1?style=for-the-badge)
![Snapdragon Ready](https://img.shields.io/badge/Snapdragon-Ready-22d3ee?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=for-the-badge)

---

## 1. Overview

**SnapAI Edge** is a private, multi-model AI assistant engineered for Snapdragon-powered PCs. Unlike conventional AI applications that lock users into a single cloud provider or force complex switching configurations, SnapAI Edge delivers a **single unified AI interface** powered by an **Intelligent AI Router**.

The core philosophy of SnapAI Edge is:
> *SnapAI Edge doesn't simply connect to multiple AI models. It intelligently decides where and how AI should run based on the task, privacy requirements, network connectivity, available models, and device capabilities.*

---

## 2. Features

* 🔀 **Unified AI Interface:** A single API layer and front-end interface connecting OpenAI, Google Gemini, Ollama, and Snapdragon local acceleration.
* 🧠 **Smart AI Router:** Autonomous request routing across `LOCAL`, `CLOUD`, `HYBRID`, and `OFFLINE` operation modes.
* 🔒 **Privacy Guard:** Pre-flight scanning for API keys, passwords, credentials, PII, and financial tokens with one-click masking and local enforcement.
* ⚡ **True Local & Offline Operation:** High-speed inference using Ollama and local runtimes with zero internet dependency and no cloud leakage.
* 🚀 **Qualcomm & Snapdragon Hardware Verification:** Genuine hardware detection for Snapdragon CPUs, Adreno GPUs, and Hexagon NPUs without synthetic capabilities.
* 📡 **Live Token Streaming:** Server-Sent Events (SSE) streaming delivering real-time tokens to the ChatGPT-style front-end.
* 📊 **Measurable Benchmarking:** Real measured metrics—Time to First Token (TTFT), tokens/sec, memory RSS, and latency—with no fabricated numbers.
* 🛡️ **Safe Error Fallback:** Automatic fallback in Auto mode, with explicit retry/switch prompts if an explicitly chosen provider fails.
* 📄 **Local RAG & Multimodal Vision:** Document indexing via ChromaDB and local/cloud vision analysis.

---

## 3. Architecture

SnapAI Edge decouples the frontend entirely from third-party AI APIs. The frontend communicates solely with the local FastAPI backend. API keys and secrets are never exposed in browser storage or client JavaScript.

```text
User Request
     ↓
SnapAI Edge Frontend (React + TypeScript + Vite)
     ↓  HTTP / SSE
FastAPI Backend
     ↓
AI Model Manager
     ↓
Smart AI Router
     ↓
┌──────────────┬──────────────┬──────────────┬────────────────────────┐
│              │              │              │                        │
▼              ▼              ▼              ▼                        ▼
OpenAI       Gemini         Ollama       Snapdragon Local        Jina AI
Cloud        Cloud          Local         Runtime (NPU/DirectML)  Embeddings/RAG
└──────────────┴──────────────┴──────────────┴────────────────────────┘
                              ↓
                       Unified Response
                              ↓
                    Performance Metrics Tracker
```

---

## 4. AI Providers

| Provider | Type | Default Model | Key Capabilities | Offline Capable |
| :--- | :--- | :--- | :--- | :---: |
| **OpenAI** | Cloud | `gpt-4o-mini` | Text, Vision, Reasoning, Coding, Streaming | ✗ |
| **Google Gemini** | Cloud | `gemini-1.5-flash` | Text, Multimodal, 1M Context, Audio, Coding | ✗ |
| **Ollama** | Local Edge | `llama3.2` | Text, Coding, Streaming, Private Inference | ✓ |
| **Snapdragon Local** | Device Runtime | `snapdragon-npu` | NPU/DirectML/CPU Edge Execution, Embeddings | ✓ |

---

## 5. OpenAI Setup

SnapAI Edge integrates OpenAI using the official Python SDK.

1. Obtain an API key from the [OpenAI Platform](https://platform.openai.com).
2. Configure `.env` in the project root:
   ```env
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_BASE_URL=https://api.openai.com/v1
   ```
3. Test your connection live in **Settings → AI Providers**.

---

## 6. Gemini Setup

SnapAI Edge connects to Google Gemini via the Google Generative AI SDK.

1. Generate an API key in [Google AI Studio](https://aistudio.google.com).
2. Add your key to `.env`:
   ```env
   GEMINI_API_KEY=
   GEMINI_MODEL=gemini-1.5-flash
   ```
3. Supported models include `gemini-1.5-flash`, `gemini-1.5-pro`, and `gemini-2.0-flash`.

---

## 7. Ollama Setup

Ollama serves as the primary local AI provider for private, offline LLM execution.

1. Download and install Ollama from [ollama.ai](https://ollama.ai).
2. Pull a recommended model:
   ```bash
   ollama pull llama3.2
   # Optional: For local vision support
   ollama pull llava
   ```
3. Configure `.env`:
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```
4. Verify daemon status: SnapAI Edge checks `http://localhost:11434/api/tags` and automatically lists installed models.

---

## 8. Local AI

Local inference runs 100% on the user's device:
* Data never leaves localhost.
* No network bandwidth consumed.
* Continues functioning in air-gapped environments.
* Large models are never downloaded automatically without explicit user confirmation.

---

## 9. Smart AI Router

The Intelligent AI Router evaluates every incoming request through an 8-stage decision pipeline:

```text
USER REQUEST
     ↓
TASK CLASSIFICATION      (Text / Vision / Coding / Reasoning / Document)
     ↓
PRIVACY ANALYSIS         (Scan for API keys, passwords, credentials, PII)
     ↓
NETWORK CHECK            (Probe online connectivity)
     ↓
LOCAL MODEL CHECK        (Verify Ollama status and installed models)
     ↓
HARDWARE CHECK           (Inspect Snapdragon NPU, DirectML, GPU, CPU)
     ↓
MODEL CAPABILITY CHECK   (Ensure model supports vision/streaming/coding)
     ↓
PERFORMANCE PREFERENCE   (AUTO, LOCAL FIRST, CLOUD FIRST, HYBRID, OFFLINE)
     ↓
MODEL SELECTION & ROUTING EXPLANATION
```

### Supported User Modes:
* **AUTO:** Evaluates task complexity, privacy, and connection to choose the best provider.
* **LOCAL FIRST:** Prioritizes local Ollama/Snapdragon runtime; falls back to cloud only if local is unavailable.
* **CLOUD FIRST:** Prefers cloud models when online; falls back to local edge when offline.
* **HYBRID:** Uses local embeddings/RAG combined with cloud or local reasoning according to task demands.
* **OFFLINE ONLY:** Strictly prohibits cloud calls. Guaranteed zero external network transmission.

---

## 10. Privacy

SnapAI Edge incorporates a built-in **Privacy Guard**:
* Scans inputs for API keys (`sk-...`, `AIza...`, `AKIA...`), passwords, authentication tokens, email addresses, phone numbers, and financial details.
* When sensitive data is detected, SnapAI Edge presents options:
  - **[Mask]:** Replaces sensitive items with safe tokens (e.g. `[MASKED_KEY]`).
  - **[Process Locally]:** Routes the request directly to local Ollama or Snapdragon runtime.
  - **[Allow Cloud]:** User explicitly overrides the warning.
  - **[Cancel]:** Aborts the prompt.

---

## 11. Offline Mode

When internet connectivity is disconnected or when **OFFLINE ONLY** mode is active:
* Cloud API calls are blocked.
* The UI displays an active `⚡ OFFLINE MODE` banner with available local models.
* Ollama and local Snapdragon runtimes handle chat, OCR, and document retrieval.
* When connectivity returns, the system automatically detects the network and restores hybrid mode.

---

## 12. Snapdragon Optimization

SnapAI Edge is designed for Qualcomm Snapdragon compute platforms:
* **Hardware Detection:** Probes CPU architecture, Qualcomm Oryon/Kryo cores, Adreno GPUs, and Hexagon NPU.
* **Honest Capability Reporting:** Uses `AVAILABLE`, `UNAVAILABLE`, and `UNKNOWN`. Never claims Snapdragon acceleration unless verified on Qualcomm hardware or supported DirectML/QNN execution providers.
* **DirectML & QNN Integration:** Supports ONNX Runtime with DirectML and QNN Execution Providers for low-power edge acceleration.

---

## 13. Benchmarking

Every inference request captures authentic, measurable performance metrics:
* **Latency (ms):** Total roundtrip execution time.
* **Time to First Token (TTFT):** Milliseconds until the first token streams.
* **Tokens per Second (TPS):** Measured decoding speed.
* **Resource Usage:** Process RSS memory and CPU percentage via `psutil`.
* **Zero Fabrication:** If a metric is unmeasured, it is displayed as `N/A`.

---

## 14. Environment Variables

Create a `.env` file in the root of `snapai-edge`:

```env
# Multi-Model AI Providers
DEFAULT_AI_PROVIDER=auto

# OpenAI Configuration
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# Google Gemini Configuration
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# Ollama Local Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Jina AI (Embeddings & RAG)
JINA_API_KEY=
JINA_EMBED_MODEL=jina-embeddings-v3

# Server Settings
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
SECRET_KEY=

# Privacy & Routing
DEFAULT_PRIVACY_MODE=local_first
ENABLE_CLOUD_AI=true
```

---

## 15. Running the Project

### Prerequisites
* Python 3.11+
* Node.js v18+ & npm
* (Optional) Ollama for local LLM execution

### 1. Install Backend Dependencies
```bash
cd snapai-edge
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
```

### 3. Start Backend & Frontend
Using PowerShell:
```powershell
./start.ps1
```
Or start manually:
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

* **Frontend:** http://localhost:5173
* **Backend API Docs:** http://localhost:8000/docs
* **Health Check:** http://localhost:8000/api/health

---

## 16. Security

* **Server-Side API Keys:** Keys are strictly read from environment variables on the backend. Frontend JavaScript, HTML, and browser storage never contain credentials.
* **Error Sanitization:** Provider exceptions are cleansed of any reflected API keys before reaching logs or client responses.
* **Prompt Injection & Overflow Protection:** Requests are validated with length limits and input boundaries.
* **No Arbitrary Execution:** SnapAI Edge does not execute unverified shell commands or run arbitrary code.

---

## 17. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **OpenAI authentication failed** | Missing or invalid key | Ensure `OPENAI_API_KEY` is set in `.env` without extra whitespace. |
| **Gemini permission denied** | Key invalid or expired | Check `GEMINI_API_KEY` in `.env` and verify quota in Google AI Studio. |
| **Ollama daemon unreachable** | Ollama service not running | Start Ollama locally by running `ollama serve`. |
| **Model not found in Ollama** | Model not pulled | Run `ollama pull llama3.2` or select an installed model from the dropdown. |
| **Snapdragon shows UNAVAILABLE** | Running on x86/AMD64 PC | Normal on non-ARM devices. SnapAI Edge will use CPU/GPU DirectML fallback. |
| **Offline banner appears** | No internet connection | Expected behavior. Local Ollama and Snapdragon models continue working. |
