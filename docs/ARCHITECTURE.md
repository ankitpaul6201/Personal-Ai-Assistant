# JARVIS AI Architecture Documentation

## System Architecture

JARVIS AI is structured as a modular, event-driven assistant built with Python 3.11+ using the Gemini Live API, PyQt6 desktop interface, and an expandable plugin-based Action Engine.

```
                    ┌───────────────────────────┐
                    │      PyQt6 GUI Avatar     │
                    │   (src/jarvis/ui.py)      │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    Main Orchestrator      │
                    │  (src/jarvis/main.py)     │
                    └──────┬─────────────┬──────┘
                           │             │
              ┌────────────┘             └────────────┐
              ▼                                       ▼
┌───────────────────────────┐           ┌───────────────────────────┐
│       Core Services       │           │       Action Engine       │
│  (src/jarvis/core/)       │           │   (src/jarvis/actions/)   │
│  • LLM Client (Gemini)    │           │  • System & App Control   │
│  • STT / TTS Pipeline     │           │  • Web Search & Browser   │
│  • Logger & Exceptions    │           │  • Dev Agent & Coding     │
│  • Resource Manager       │           │  • Computer Vision        │
└─────────────┬─────────────┘           └───────────────────────────┘
              │
              ▼
┌───────────────────────────┐
│     Memory & Persistence  │
│  (src/jarvis/memory/)     │
│  • Long Term Memory       │
│  • Config Manager         │
└───────────────────────────┘
```

---

## Key Modules

### 1. Package Entrypoints (`src/jarvis/`)
- `main.py`: Entry point for the main asyncio event loop, Gemini Live session management, audio stream handling, and dispatching tool/action calls.
- `ui.py`: PyQt6 application interface rendering dynamic avatar graphics, voice activity visualizers, terminal outputs, and system settings.

### 2. Core Package (`src/jarvis/core/`)
- `llm_client.py`: High-level wrapper for Google GenAI Live client, handling audio streaming, function calling schemas, and prompt generation.
- `stt.py` & `tts.py`: Speech-to-Text and Text-to-Speech engines supporting low-latency local audio conversion.
- `security.py`: Security validation for path traversal prevention, shell argument sanitization, and credential masking.
- `resource_manager.py`: Cross-platform path resolution for PyInstaller bundles and dev runtimes.

### 3. Action Engine (`src/jarvis/actions/`)
Modular action plugins that JARVIS executes on demand:
- `browser_control.py` / `web_search.py`: Playwright web automation and Google search.
- `computer_control.py` / `file_controller.py`: System input automation, file manipulation, and desktop shortcuts.
- `dev_agent.py` / `code_helper.py`: Automated code generation, file editing, and project analysis.
- `screen_processor.py`: Real-time screen capture and visual analysis.

### 4. Memory & Dashboard (`src/jarvis/memory/` & `src/jarvis/dashboard/`)
- `memory_manager.py`: Long-term persistent memory manager (`long_term.json`) storing user context, preferences, and assistant identity.
- `server.py`: Lightweight FastAPI web dashboard server monitoring assistant status, logs, and system metrics.
