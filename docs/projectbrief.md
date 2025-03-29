# Syllablaze Project Summary

## Core Purpose
- Local, privacy-focused speech-to-text for KDE Plasma
- Real-time transcription using OpenAI Whisper (local processing)
- Designed for Ubuntu KDE with cross-distro potential

## Key Features
1. **Audio Processing**:
   - In-memory recording (no temp files)
   - Direct 16kHz capture for efficiency
   - System microphone integration

2. **Transcription**:
   - Local Whisper model processing
   - Multiple model size options
   - Automatic clipboard integration

3. **UI/UX**:
   - System tray integration
   - Global keyboard shortcuts
   - Model management interface
   - Progress feedback

## Target Users
- Students, professionals, content creators
- Accessibility users
- Privacy-conscious individuals
- KDE enthusiasts

## Technical Stack
- Python 3.8+, PyQt6, Whisper, PyAudio
- KDE Plasma integration
- User-level installation via pipx