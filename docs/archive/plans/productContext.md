# Syllablaze Product Context

## Purpose
- Bridges spoken-word-to-text gap with local, privacy-focused solution
- Processes audio locally using Faster Whisper implementation
- Provides real-time transcription with minimal latency
- Designed specifically for KDE Plasma desktop environment

## Key Benefits
1. **Efficiency**: Saves time vs manual transcription (90%+ accuracy)
2. **Accessibility**: Helps those preferring speech over typing
3. **Privacy**: No cloud processing of audio (100% local processing)
4. **Flexibility**: Adjustable model sizes (tiny to large) for performance/accuracy balance
5. **Integration**: Seamless KDE Plasma experience with system tray and global shortcuts

## Core Workflow
1. **Recording**:
   - Start via system tray menu or global shortcut (Ctrl+Alt+R)
   - Visual feedback with recording dialog and volume meter
   - Automatic microphone configuration from settings
   - In-memory audio buffer (16kHz, mono)

2. **Processing**:
   - Local Faster Whisper model transcribes audio
   - Progress updates during transcription
   - Configurable parameters (beam size, VAD filter, word timestamps)
   - Language auto-detection with manual override

3. **Output**:
   - Text auto-copied to clipboard (default)
   - Option to send to active window
   - Notification on completion
   - Error handling for no-voice-detected cases

4. **Configuration**:
   - Input device selection with test functionality
   - Model selection and management
   - Shortcut customization
   - Language preferences
   - Transcription quality settings

## UX Goals
- Simple, reliable, responsive KDE integration
- Minimal disruption with clear feedback:
  - Recording status indicators
  - Progress updates
  - Volume monitoring
  - Error notifications
- Resource-aware for various hardware:
  - Automatic hardware detection (CPU/GPU)
  - Model size recommendations
  - Performance monitoring

## Target Users
- Students and researchers for lecture/meeting notes
- Professionals for dictation and documentation
- Content creators for transcription
- Accessibility users for voice interaction
- Privacy-conscious users avoiding cloud services
- KDE Plasma desktop users
- Linux users needing reliable STT

## Model Management
- Clear model info (size, status, storage requirements)
- Download/delete control
- Performance/accuracy tradeoff selection
- Automatic model verification
- Hardware-optimized loading
- Model change detection and reloading