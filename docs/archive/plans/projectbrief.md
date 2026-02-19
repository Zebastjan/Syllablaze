# Syllablaze Project Summary

## Core Purpose
- Local, privacy-focused speech-to-text (STT) for KDE Plasma
- Real-time transcription using local Whisper models (Faster Whisper implementation)
- Optimized for Ubuntu KDE with cross-distro support
- Version: 0.4 beta

## Key Features
1. **Audio Processing**:
   - In-memory recording (16kHz direct capture)
   - System microphone integration with device selection
   - Volume monitoring and testing
   - Automatic sample rate configuration

2. **Transcription**:
   - Local Whisper models (tiny, base, small, medium, large, turbo)
   - Auto clipboard integration
   - Language auto-detection with manual override
   - Configurable transcription parameters (beam size, VAD filter, word timestamps)

3. **Model Management**:
   - Model download and selection
   - Automatic hardware detection (CPU/GPU)
   - Optimal compute type configuration

4. **UI/UX**:
   - System tray integration
   - Global shortcuts (Ctrl+Alt+R)
   - Progress feedback during recording/transcription
   - Modern Qt interface with theme support
   - Microphone testing functionality

## Target Users
- Students and researchers for lecture/meeting notes
- Professionals for dictation and documentation
- Content creators for transcription
- Accessibility users for voice interaction
- Privacy-conscious users avoiding cloud services
- KDE Plasma desktop users
- Linux users needing reliable STT

## Technical Stack
- Python 3.8+
- PyQt6 for GUI
- Faster Whisper for transcription
- PyAudio for audio capture
- NumPy for audio processing
- KDE Plasma integration (XDG compliant)
- pipx user-level installation
- System tray via Qt