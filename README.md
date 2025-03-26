# Syllablaze for KDE Plasma

A sleek KDE Plasma application that records audio and transcribes it in real-time using OpenAI's Whisper. Originally created by Guilherme da Silveira as "Telly Spelly", now enhanced for Ubuntu KDE compatibility.

## Features

- 🎙️ **Easy Recording**: Start/stop recording with a single click in the system tray
- 🔊 **Live Volume Meter**: Visual feedback while recording
- ⚡ **Global Shortcuts**: Configurable keyboard shortcuts for quick recording
- 🎯 **Microphone Selection**: Choose your preferred input device
- 📋 **Instant Clipboard**: Transcribed text is automatically copied to your clipboard
- 🎨 **Native KDE Integration**: Follows your system theme and integrates seamlessly with Plasma

## Installation

### Prerequisites

Before installing Syllablaze, ensure you have the necessary system dependencies:

#### Ubuntu/Debian (including Ubuntu KDE)

```bash
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev ffmpeg
```

#### Fedora

```bash
sudo dnf install -y python3-libs python3-devel python3 portaudio-devel ffmpeg
```

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/gbasilveira/syllablaze.git
cd syllablaze
```

2. Run the installer:
```bash
python3 install.py
```

The installer will:
- Check for required system dependencies
- Install all required Python packages
- Set up the application in your user directory
- Create desktop entries and icons
- Configure the launcher

### Ubuntu KDE Specific Notes

The installer has been optimized for Ubuntu KDE with:
- Improved system dependency checks
- Better error handling for ALSA libraries
- Installation verification
- Support for Ubuntu-specific library paths

## Requirements

- Python 3.8 or higher
- KDE Plasma desktop environment
- PortAudio (for audio recording)
- CUDA-capable GPU (optional, for faster transcription)

## Usage

1. Launch "Syllablaze" from your application menu or run:
```bash
syllablaze
```

2. Click the tray icon or use configured shortcuts to start/stop recording
3. When recording stops, the audio will be automatically transcribed
4. The transcribed text is copied to your clipboard

## Configuration

- Right-click the tray icon and select "Settings"
- Configure:
  - Input device selection
  - Global keyboard shortcuts
  - Whisper model selection
  - Interface preferences

## Uninstallation

To remove the application:
```bash
python3 uninstall.py
```

## Troubleshooting

### Common Issues on Ubuntu KDE

1. **Application doesn't appear in menu**
   - Log out and log back in to refresh the application menu
   - Verify installation with `ls -la ~/.local/share/applications/org.kde.syllablaze.desktop`

2. **Audio recording issues**
   - Ensure your microphone is properly configured in KDE System Settings
   - Add your user to the audio group: `sudo usermod -a -G audio $USER`

3. **ALSA errors**
   - The application attempts to suppress common ALSA errors
   - If you see ALSA errors, try installing: `sudo apt install -y libasound2-dev`

4. **Slow transcription**
   - For faster transcription, install CUDA if you have an NVIDIA GPU:
     `sudo apt install -y nvidia-cuda-toolkit`
   - Select a smaller model in the settings

## Technical Details

- Built with PyQt6 for the GUI
- Uses OpenAI's Whisper for transcription
- Integrates with KDE Plasma using system tray and global shortcuts
- Records audio using PyAudio
- Processes audio with scipy for optimal quality

## Contributing

Contributions are welcome! Feel free to:
- Report issues
- Suggest features
- Submit pull requests

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the amazing speech recognition model
- KDE Community for the excellent desktop environment
- All contributors and users of this project

## Author

**Guilherme da Silveira** (Original creator)

---

Made with ❤️ for the KDE Community
