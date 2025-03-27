# Syllablaze v0.2 for KDE Plasma

Real-time audio transcription app using OpenAI's Whisper. Originally created by Guilherme da Silveira as "Telly Spelly".

## Features

- 🎙️ One-click recording from system tray
- 🔊 Live volume meter
- ⚡ Global keyboard shortcuts
- 🎯 Microphone selection
- 📋 Auto clipboard copy
- 🎨 Native KDE integration

## Installation

### Prerequisites

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev ffmpeg
```

#### Fedora
```bash
sudo dnf install -y python3-libs python3-devel python3 portaudio-devel ffmpeg
```

### Install
```bash
git clone https://github.com/PabloVitasso/Syllablaze.git
cd Syllablaze
python3 install.py
```

## Usage

1. Launch "Syllablaze" from application menu
2. Click tray icon or use shortcuts to start/stop recording
3. Transcribed text is copied to clipboard

## Configuration

Right-click tray icon → Settings to configure:
- Input device
- Keyboard shortcuts
- Whisper model
- Interface preferences

## Uninstall
```bash
python3 uninstall.py
```

## Requirements

- Python 3.8+
- KDE Plasma
- PortAudio
- CUDA GPU (optional)

## Memory Bank Files

The [Memory Bank files](docs/) in the `docs/` directory provide comprehensive documentation of the project:

- [Project Brief](docs/projectbrief.md) - Core requirements and goals
- [Product Context](docs/productContext.md) - Why this project exists and how it works
- [System Patterns](docs/systemPatterns.md) - Architecture and design patterns
- [Tech Context](docs/techContext.md) - Technologies and dependencies
- [Active Context](docs/activeContext.md) - Current work focus and recent changes
- [Progress](docs/progress.md) - Current status and known issues

These documentation files were created by an AI assistant (Roo) operated by RooCode, using OpenRouter Claude Sonnet 3.7.

## License

MIT License

## Author

**Guilherme da Silveira** (Original creator)

