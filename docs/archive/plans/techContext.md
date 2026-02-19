# Syllablaze Technical Summary

## Architecture
```mermaid
flowchart TD
    UI[User Interface] -->|controls| Rec[Audio Recording]
    UI -->|configures| Settings
    Rec -->|processes| Audio
    Audio -->|transcribes| Whisper
    Whisper -->|outputs| Clipboard
    Settings -->|manages| Models
    Models -->|feeds| Whisper
```

## Core Components
- **TrayRecorder**: Main controller
- **AudioRecorder**: Microphone handling
- **WhisperTranscriber**: Transcription
- **SettingsWindow**: Configuration
- **ModelManager**: Whisper model handling

## Tech Stack
- **GUI**: PyQt6
- **STT**: OpenAI Whisper
- **Audio**: PyAudio, ALSA/PulseAudio
- **Math**: NumPy/SciPy
- **Integration**: KDE Plasma, XDG

## Model Management
- Table UI for model selection
- Download/delete functionality (150MB-3GB/models)
- Filesystem-based detection
- Threaded downloads