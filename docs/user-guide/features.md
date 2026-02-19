# Features Overview

Syllablaze provides real-time speech-to-text transcription with privacy and KDE Plasma integration.

## Core Features

### Real-Time Transcription
- Speech-to-text using OpenAI's Whisper models
- Powered by faster-whisper for 2-4x performance improvement
- Multiple model sizes: tiny, base, small, medium, large
- Support for 90+ languages with automatic detection

### Privacy-Focused Design
- **No temp files:** All audio processing in-memory
- **No cloud:** Everything runs locally on your machine
- **Direct 16kHz recording:** Minimal quality, maximum privacy
- **Secure:** No data leaves your computer

### KDE Plasma Integration
- Native Kirigami UI matching Plasma styling
- System tray integration
- Global keyboard shortcuts via KGlobalAccel
- KWin window management integration
- Works on both X11 and Wayland

## UI Features

### Recording Indicators

Choose from three visualization styles:

1. **None:** No visual indicator (minimal distraction)
2. **Traditional:** Progress bar window (classic UI)
3. **Applet:** Circular waveform with real-time visualization (recommended)

See [Recording Modes](recording-modes.md) for detailed comparison.

### Interactive Recording Dialog

The Applet mode provides:
- Real-time volume visualization (green → yellow → red)
- Click to toggle recording
- Drag to reposition
- Scroll to resize (100-500px)
- Right-click context menu
- Auto-hide or persistent modes

## Audio Features

### Microphone Selection
- Automatic device detection via PyAudio
- Dropdown selector in settings
- Intelligent filtering of output-only devices
- Support for USB and Bluetooth microphones

### Sample Rate Modes
- **Whisper (16 kHz):** Direct recording at Whisper's native rate (recommended)
- **Device Native:** Use mic's native sample rate with resampling

## Transcription Features

### Model Selection
- Download and switch between Whisper models on-the-fly
- Model management: download, delete, verify
- Progress tracking for downloads
- Automatic CUDA detection for GPU acceleration

### Quality Controls
- **Beam Size:** 1-10 (higher = better accuracy, slower)
- **VAD Filter:** Remove silence before transcription
- **Word Timestamps:** Enable word-level timing (future feature)
- **Compute Type:** auto, float32, float16 (GPU), int8 (CPU)

### Language Support
- 90+ languages supported
- Automatic language detection
- Manual language selection for better accuracy
- English-only models (`.en`) for English-only use

## Keyboard Shortcuts

### Global Shortcuts
- System-wide hotkey registration
- Default: Alt+Space to toggle recording
- Fully customizable shortcut
- Works on KDE Wayland, X11, and other DEs

### Integration
- KGlobalAccel D-Bus on KDE Plasma (native)
- pynput fallback for other desktop environments
- Prevents accidental triggers during transcription

## Performance Features

### GPU Acceleration
- Automatic CUDA detection
- LD_LIBRARY_PATH configuration
- 5-10x faster transcription on NVIDIA GPUs
- Automatic fallback to CPU if GPU unavailable

### Optimization
- Direct 16kHz recording (no resampling)
- In-memory processing (no disk I/O)
- faster-whisper backend (CTranslate2 optimized)
- VAD filter reduces transcription time

## Clipboard Integration

### Persistent Clipboard Service
- Transcription automatically copied to clipboard
- Wayland-compatible clipboard persistence
- Works even when recording dialog is hidden
- Paste transcription anywhere with Ctrl+V

## Settings Management

### Modern Settings Window
- Kirigami-based UI matching KDE Plasma
- Organized into 6 pages: Models, Audio, Transcription, Shortcuts, UI, About
- Visual 3-card selector for popup styles
- Conditional settings based on selections
- High-DPI support

### Settings Persistence
- QSettings-based storage (`~/.config/Syllablaze/`)
- Settings survive application restarts
- Import/export settings (future feature)

## System Integration

### Single Instance Enforcement
- Lock file prevents multiple instances
- D-Bus activation for subsequent launches
- Brings existing instance to foreground

### Startup Options
- Launch on login (manual .desktop edit)
- Start minimized to tray
- Auto-download default model on first run

## Platform Support

### Desktop Environments
- **KDE Plasma:** Full support (Wayland + X11)
- **GNOME:** Partial support (X11 only)
- **Other DEs:** Basic support (X11)

### Session Types
- **Wayland:** Supported with KWin-specific features
- **X11:** Full support on all DEs

See [Wayland Support](../explanation/wayland-support.md) for details on Wayland-specific behavior.

## Upcoming Features

See [Roadmap](../roadmap/) for planned features and known issues.

---

**Related Documentation:**
- [Settings Reference](settings-reference.md) - All settings explained
- [Recording Modes](recording-modes.md) - Visual indicator comparison
- [Quick Start](../getting-started/quick-start.md) - Get started in 5 minutes
