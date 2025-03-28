# Syllablaze v0.3 for KDE Plasma

Real-time audio transcription app using OpenAI's Whisper.

Originally created by Guilherme da Silveira as "Telly Spelly".

## Features

- One-click recording from system tray
- Live volume meter
- Global keyboard shortcuts
- Microphone selection
- Auto clipboard copy
- Native KDE integration
- In-memory audio processing (no temporary files)
- Direct 16kHz recording for improved privacy and reduced file size

## What's New in v0.3

- **Enhanced Privacy**: Audio is now processed entirely in memory without writing to disk at any point
- **Improved Performance**: Direct 16kHz recording reduces processing time and memory usage
- **Better Security**: No temporary files means no risk of sensitive audio data being left on disk
- **Reduced Resource Usage**: Streamlined audio processing pipeline for more efficient operation

## Screenshots
tray icon:

<img src="https://github.com/user-attachments/assets/7c1a0b3f-6606-4970-9ad9-337e88ddecfe" width="300px">

click on the tray icon opens speech recognition: 

<img src="https://github.com/user-attachments/assets/91aa090c-d0e2-414f-bbcc-780f182d4030" width="400px">

notification after action:

<img src="https://github.com/user-attachments/assets/4f58b335-4dd3-4db5-a73c-9f4fcd11f1d8" width="350px">

text automatically lands into clipboard:

<img src="https://github.com/user-attachments/assets/7821a6ad-614e-4e47-bcef-ce6f6e8ab027" width="400px">

settings screen:

<img src="https://github.com/user-attachments/assets/5ca8a113-64b5-40e7-b200-e38779cab078" width="500px">


## Project Structure

- `blaze/` - Core application files
- `docs/` - Documentation files
- `install.py` - Installation script 
- `uninstall.py` - Uninstallation script


## Installation

### Prerequisites

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev ffmpeg python3-pipx
```

#### Fedora
```bash
sudo dnf install -y python3-libs python3-devel python3 portaudio-devel ffmpeg pipx
```

The setup script will automatically install these dependencies if they are missing.

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
or

```bash
pipx uninstall syllablaze
```



## Requirements

- Python 3.8+
- KDE Plasma

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

