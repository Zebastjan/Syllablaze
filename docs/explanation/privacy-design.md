# Privacy Design

Syllablaze is designed with privacy as a core principle. This document explains the privacy-focused design decisions.

## Core Privacy Principles

1. **Local Processing:** All transcription happens on your machine
2. **No Temp Files:** Audio never written to disk
3. **No Cloud:** No data sent to external servers
4. **Minimal Quality:** Record at lowest quality sufficient for transcription
5. **Ephemeral Data:** Audio cleared from memory after transcription

## In-Memory Processing

### Decision

All audio processing happens in memory without writing temporary files.

### Implementation

**Recording:**
```python
# blaze/recorder.py
class AudioRecorder:
    def __init__(self):
        self.audio_frames = []  # NumPy array, in-memory only

    def _audio_callback(self, in_data, frame_count, time_info, status):
        # Convert to numpy array directly in memory
        audio_array = np.frombuffer(in_data, dtype=np.int16)
        self.audio_frames.append(audio_array)
        # Never writes to disk
```

**Transcription:**
```python
# blaze/transcriber.py
class FasterWhisperTranscriptionWorker:
    def run(self):
        # audio_data is numpy array (in-memory)
        segments, info = self.model.transcribe(self.audio_data)
        # No temp files created
```

### Why This Matters

**Traditional approach (many transcription apps):**
```python
# Bad: writes to disk
with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
    tmp.write(audio_data)
    result = transcribe(tmp.name)
```

**Problems:**
- Temp file persists if app crashes
- Forensic recovery possible even after deletion
- Disk I/O is slower than memory
- File permissions can leak data

**Syllablaze approach:**
```python
# Good: stays in memory
audio_array = np.array(audio_frames)  # RAM only
result = model.transcribe(audio_array)
del audio_array  # Cleared by garbage collector
```

**Advantages:**
- No disk trace of audio
- Faster (no I/O overhead)
- No file permission issues
- Memory cleared when variable scope ends

## Direct 16kHz Recording

### Decision

Record at 16kHz directly instead of higher quality with downsampling.

### Rationale

**Whisper models require 16kHz input:**
- Higher sample rates provide no accuracy benefit
- Lower sample rates lose fidelity

**Privacy benefit:**
- 16kHz captures speech frequencies (human voice < 8kHz per Nyquist)
- Higher frequencies (music quality) not captured
- Lower quality = less sensitive data

**Comparison:**

| Sample Rate | Use Case | Quality | File Size |
|-------------|----------|---------|-----------|
| 8 kHz | Phone call | Low | Smallest |
| 16 kHz | **Speech (Whisper)** | **Sufficient** | **Small** |
| 44.1 kHz | CD audio | High | Large |
| 48 kHz | Professional | Very high | Larger |

**Recording at 44.1kHz then downsampling:**
- Captures more detail than needed
- Larger in-memory buffer (2.75x larger)
- Downsample step adds CPU overhead
- No transcription accuracy improvement

**Recording at 16kHz directly:**
- Minimal quality for speech
- Smaller memory footprint
- No resampling needed
- Same transcription accuracy

### Implementation

```python
# blaze/constants.py
WHISPER_SAMPLE_RATE = 16000

# blaze/recorder.py
stream = pyaudio.open(
    rate=WHISPER_SAMPLE_RATE,  # Direct 16kHz recording
    # ...
)
```

**Settings option:** "Device Native" mode available for compatibility (resamples afterward).

## No Cloud, All Local

### Model Download

**First run only:**
- Downloads Whisper model from Hugging Face Hub
- Stored locally: `~/.cache/huggingface/hub/`
- One-time download, used offline afterward

**All transcription is local:**
- No API calls to OpenAI or other services
- No internet required after model download
- No usage telemetry or analytics

### No Telemetry

Syllablaze does not collect:
- Usage statistics
- Error reports (unless manually submitted via GitHub)
- Audio samples
- Transcription results
- System information

**Exception:** Manual bug reports via GitHub Issues (user provides logs voluntarily).

## Data Lifecycle

### During Recording

1. Microphone input → PyAudio callback
2. Raw bytes → NumPy array (in-memory)
3. Arrays appended to list (in-memory)
4. **No disk writes**

### During Transcription

1. NumPy arrays concatenated
2. Passed to faster-whisper model (in-memory)
3. Model processes audio (CPU/GPU, no disk)
4. Text result returned
5. **Audio data discarded** (garbage collected)

### After Transcription

1. Text copied to clipboard (system clipboard manager)
2. Audio data reference cleared: `self.audio_frames = []`
3. Python garbage collector frees memory
4. **No audio remains in memory**

## Settings Privacy

### What's Stored

**Settings file:** `~/.config/Syllablaze/Syllablaze.conf`

**Contents:**
- Preferences (model size, language, shortcuts)
- Window positions and sizes
- UI configuration

**NOT stored:**
- Audio recordings
- Transcription results
- Microphone input
- Usage history

### Settings Deletion

Uninstalling Syllablaze does NOT delete settings (preserves user preferences for reinstall).

**To delete all data:**
```bash
python3 uninstall.py  # Remove app
rm -rf ~/.config/Syllablaze/  # Remove settings
rm -rf ~/.cache/huggingface/hub/models--openai--*  # Remove models (optional)
```

## Clipboard Security

### Clipboard Manager Persistence

**Issue:** On Wayland, clipboard data is lost when source app hides window.

**Solution:** `ClipboardManager` keeps data in memory even when recording dialog hidden.

**Privacy consideration:**
- Transcription text persists in memory until app quits or new transcription overwrites it
- Clipboard is system-managed (paste buffer shared with other apps)

**Mitigation:**
- User can clear clipboard manually
- App restart clears clipboard manager memory

## Model Security

### Where Models Are Stored

```
~/.cache/huggingface/hub/
└── models--openai--whisper-<size>/
    ├── blobs/
    └── snapshots/
```

**Security:**
- File permissions: User-only read/write
- Downloaded via HTTPS
- Checksums verified by huggingface_hub library

### Model Deletion

Settings → Models → Delete removes model files from cache.

## Recommendations for Maximum Privacy

1. **Use smaller models:**
   - Less disk space used
   - Faster transcription (less time audio in memory)

2. **Clear clipboard after paste:**
   - Prevents transcription from persisting in clipboard

3. **Encrypt home directory:**
   - Settings and models stored under `~/.config/` and `~/.cache/`
   - Full-disk encryption protects at rest

4. **Use None popup mode:**
   - No visual indicator (no shoulder surfing)
   - Minimal UI code path (less potential for leaks)

5. **Disable debug logging:**
   - Debug logs may contain audio buffer metadata
   - Settings → About → Debug Logging → OFF (default)

## Future Privacy Enhancements

Potential future improvements:

- **Secure memory:** Use `mlock()` to prevent swap
- **Zero on free:** Explicitly zero audio arrays before deallocation
- **Transcription history:** Optional in-memory history with manual clear
- **End-to-end encryption:** Encrypt settings file (overkill for current data)

---

**Related Documentation:**
- [Design Decisions](design-decisions.md#privacy-first) - Privacy-focused design rationale
- [Features Overview](../user-guide/features.md#privacy-focused-design) - User-facing privacy features
