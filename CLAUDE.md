# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Syllablaze is a PyQt6 system tray application for real-time speech-to-text transcription using OpenAI's Whisper (via faster-whisper). It records audio, transcribes it, and copies the result to clipboard. Targets KDE Plasma on Wayland/X11 Linux desktops. Installed as a user-level package via pipx.

## Build and Run Commands

```bash
# Install (user-level via pipx)
python3 install.py

# Run directly during development
python3 -m blaze.main

# Dev update: copies to pipx install dir, restarts app
# NOTE: Ruff has been DISABLED during debugging sessions
./blaze/dev-update.sh

# Uninstall
python3 uninstall.py
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_audio_processor.py

# Run specific test
pytest tests/test_audio_processor.py::test_frames_to_numpy

# Run by marker: unit, integration, audio, ui, settings, core
pytest -m audio
```

pytest config is in `tests/pytest.ini`. Fixtures and mocks (MockPyAudio, MockSettings, sample audio data) are in `tests/conftest.py`.

## Linting

CI uses **flake8** (max-line-length=127, max-complexity=10). Dev workflow uses **ruff** optionally. No formatter (black/autopep8) is configured.

```bash
flake8 . --max-line-length=127
# ruff check blaze/ --fix  # DISABLED during active debugging
```

## Architecture

**Entry point**: `blaze/main.py` - `main()` function creates the Qt application, initializes `ApplicationTrayIcon` (the main controller), sets up D-Bus service (`SyllaDBusService`), and starts a qasync event loop.

**Core flow**:
```
ApplicationTrayIcon (main.py) - orchestrator
  ├── AudioManager -> AudioRecorder (recorder.py) -> PyAudio microphone input
  ├── TranscriptionManager -> FasterWhisperTranscriptionWorker (transcriber.py)
  ├── UIManager -> ProgressWindow, LoadingWindow, ProcessingWindow
  ├── GlobalShortcuts (shortcuts.py) -> pynput keyboard listener
  ├── LockManager -> single-instance enforcement via lock file
  └── ClipboardManager -> copies transcription to clipboard
```

**Manager pattern** (`blaze/managers/`): AudioManager, TranscriptionManager, UIManager, and LockManager separate concerns from the main controller.

**Key design decisions**:
- All inter-component communication uses Qt signals/slots (thread-safe)
- Audio recorded at 16kHz directly (optimized for Whisper, no resampling needed)
- Audio processed entirely in memory (no temp files to disk)
- Global shortcuts use KDE kglobalaccel D-Bus integration; default is Alt+Space
- WhisperModelManager (`blaze/whisper_model_manager.py`) handles model download/deletion/GPU detection
- Settings persisted via QSettings (`blaze/settings.py`)
- Constants (app version, sample rates, defaults) in `blaze/constants.py`

**UI windows** are separate classes: `KirigamiSettingsWindow` (QML-based), `ProgressWindow`, `LoadingWindow`, `ProcessingWindow`, `VolumeMeter`.

## UI Architecture

Settings window uses **Kirigami QML UI** (`blaze/kirigami_integration.py`):
- Modern KDE Plasma styling matching the desktop environment
- QML pages in `blaze/qml/pages/` (Models, Audio, Transcription, Shortcuts, About)
- Python-QML bridge via `SettingsBridge` for bidirectional communication
- Display scaling support via `devicePixelRatio` detection
- Replaces old PyQt6 widget UI (removed in commit 0031ca5)

## Development Workflow

Use standard git branch workflow:
- `main` branch = stable production version
- Feature branches = development work
- Editable pipx install picks up changes immediately
- Switch branches and restart app to test different versions

```bash
# Work on feature
git checkout feature-branch
pkill syllablaze
syllablaze

# Test stable
git checkout main
pkill syllablaze
syllablaze
```

## Key Dependencies

PyQt6, faster-whisper (>=1.1.0), pyaudio, numpy, scipy, pynput, dbus-next, qasync, psutil, keyboard, hf_transfer

## CI

GitHub Actions (`.github/workflows/python-app.yml`): Python 3.10, flake8 lint, pytest. Runs on push/PR to main.
