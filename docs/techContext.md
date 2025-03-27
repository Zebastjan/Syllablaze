# Syllablaze Technical Context

## Technologies Used

### Core Technologies

1. **Python 3.8+**: The primary programming language
2. **PyQt6**: GUI framework for creating the user interface
3. **OpenAI Whisper**: AI model for speech-to-text transcription
4. **PyAudio**: Library for audio recording and processing
5. **SciPy**: Used for audio signal processing
6. **NumPy**: Numerical processing for audio data

### System Integration

1. **KDE Plasma**: Desktop environment integration
2. **D-Bus**: For system service communication
3. **XDG Standards**: For application installation and desktop integration
4. **ALSA/PulseAudio**: Audio system integration

## Development Setup

### Required Tools

1. **Python 3.8+**: Core runtime environment
2. **pipx**: Python application installer
3. **Git**: Version control
4. **ffmpeg**: Audio processing dependency
5. **PortAudio**: Audio recording library

### System Dependencies

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y python3-pipx python3-dev portaudio19-dev ffmpeg
```

#### Fedora

```bash
sudo dnf install -y python3-pipx python3-devel python3 portaudio-devel ffmpeg
```

### Python Dependencies

```
PyQt6
numpy
pyaudio
scipy
openai-whisper (from PyPI)
```

## Technical Constraints

1. **Processing Power**: Whisper transcription can be resource-intensive
   - Recommended: Multi-core CPU for faster processing
   - Optional: CUDA-capable GPU for significantly faster transcription

2. **Audio Quality**: Transcription accuracy depends on audio quality
   - Recommended: Good quality microphone
   - Constraint: Background noise can affect transcription accuracy

3. **Disk Space**: Whisper models require storage space
   - Small model: ~150MB
   - Medium model: ~500MB
   - Large model: ~1.5GB

4. **Memory Usage**: Larger Whisper models require more RAM
   - Minimum: 4GB RAM
   - Recommended: 8GB+ RAM for larger models

5. **Installation Permissions**: User-level installation only
   - Application installs to user's home directory
   - No system-wide installation option currently

6. **Desktop Environment**: Optimized for KDE Plasma
   - May work in other environments but with limited integration

7. **Whisper API Limitations**: The Whisper API has certain limitations
   - No direct method to check which models are downloaded without loading them
   - No direct method to get download progress
   - No direct method to delete models
   - Workarounds implemented in the WhisperModelManager class

## Dependencies

### Direct Dependencies

1. **PyQt6**: GUI framework
   - Purpose: Provides the user interface components
   - Criticality: High (core functionality)

2. **PyAudio**: Audio recording
   - Purpose: Captures audio from microphone
   - Criticality: High (core functionality)
   - System requirements: PortAudio development files

3. **Whisper**: Transcription
    - Purpose: Converts speech to text
    - Criticality: High (core functionality)
    - Installation: From official PyPI repository as 'openai-whisper'
    - System requirements: ffmpeg

4. **NumPy/SciPy**: Audio processing
   - Purpose: Process audio data for optimal transcription
   - Criticality: Medium (enhances quality)

### Indirect Dependencies

1. **ffmpeg**: Required by Whisper for audio processing
   - Must be installed at the system level

2. **PortAudio**: Required by PyAudio for microphone access
   - Must be installed at the system level

3. **Qt Libraries**: Required by PyQt6
   - Installed automatically with PyQt6

## Ubuntu KDE Specific Considerations

1. **Library Paths**: Ubuntu may have different paths for system libraries
   - ALSA library: Typically at `/usr/lib/x86_64-linux-gnu/libasound.so.2`
   - Fallback paths should be included for compatibility

2. **Desktop Integration**: KDE on Ubuntu has specific paths
   - Applications: `~/.local/share/applications/`
   - Icons: `~/.local/share/icons/hicolor/256x256/apps/`

3. **System Dependencies**: Ubuntu package names
   - `python3-dev` instead of `python3-devel` (Fedora)
   - `portaudio19-dev` instead of `portaudio-devel` (Fedora)

4. **Error Handling**: Ubuntu-specific considerations
   - ALSA errors should be suppressed with appropriate error handlers
   - PulseAudio integration should be verified

## Development Environment

1. **Recommended IDE**: Visual Studio Code with Python extension
2. **Debugging**: PyQt debugger or standard Python debugger
3. **Testing**: Manual testing of recording and transcription
4. **Version Control**: Git with GitHub for collaboration
5. **Development Update Script**: `blaze/dev-update.sh` for quickly updating an installed version with development changes
   - Purpose: Updates an installed Syllablaze with current repository files without reinstalling
   - Usage: Run `bash ./blaze/dev-update.sh` from the project root directory
   - Function: Copies all Python files and the run script to the installed location

## Whisper Model Management

### Model Storage

1. **Location**: Models are stored in `~/.cache/whisper/` directory
2. **Format**: Models are stored as `.pt` files (PyTorch format)
3. **Naming**: Models are named according to their size (e.g., `tiny.pt`, `base.pt`, etc.)

### Model Information

1. **Available Models**:
   - tiny: ~150MB, very fast but basic accuracy
   - base: ~300MB, fast with good accuracy
   - small: ~500MB, medium speed with very good accuracy
   - medium: ~1.5GB, slow with excellent accuracy
   - large: ~3GB, very slow with superior accuracy

2. **Model Detection**:
   - The application scans the Whisper cache directory to detect downloaded models
   - It checks for the existence of model files with the exact name pattern

3. **Model Download**:
   - Downloads are handled by the Whisper API's `load_model()` function
   - The application simulates download progress since the API doesn't provide direct progress tracking
   - Downloads run in a separate thread to keep the UI responsive

4. **Model Deletion**:
   - The application directly deletes model files from the cache directory
   - It prevents deletion of the currently active model

### UI Components

1. **WhisperModelTable**: A custom widget that displays and manages Whisper models
   - Shows model name, status (downloaded/not downloaded), and size
   - Provides buttons to download, delete, or set a model as active
   - Highlights the currently active model

2. **ModelDownloadDialog**: A dialog that shows download progress
   - Displays a progress bar, status text, and estimated time remaining
   - Updates smoothly using a timer to simulate download progress

3. **ModelDownloadThread**: A thread that handles model downloads
   - Runs the download operation in the background
   - Emits signals to update the UI with progress information