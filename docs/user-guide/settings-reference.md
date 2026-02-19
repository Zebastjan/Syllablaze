# Settings Reference

Complete reference for all Syllablaze settings. Access settings via tray icon → Settings or global shortcut (default: Alt+S).

## Settings Organization

Settings are organized into six pages:

- **[Models](#models-page)** - Whisper model selection and management
- **[Audio](#audio-page)** - Microphone and audio configuration
- **[Transcription](#transcription-page)** - Transcription quality and performance
- **[Shortcuts](#shortcuts-page)** - Global keyboard shortcuts
- **[UI](#ui-page)** - Visual indicators and window behavior
- **[About](#about-page)** - Version info, debug logging, credits

---

## Models Page

### Selected Model

- **Type:** Dropdown selector
- **Default:** `base`
- **Options:** `tiny`, `tiny.en`, `base`, `base.en`, `small`, `small.en`, `medium`, `medium.en`, `large-v1`, `large-v2`, `large-v3`
- **Description:**
  Whisper model to use for transcription. Larger models provide better accuracy but require more resources.

  **Model comparison:**
  - `tiny` (39M params): Fastest, lowest accuracy, ~500 MB RAM, ~1 GB disk
  - `base` (74M params): Good balance, ~800 MB RAM, ~2 GB disk
  - `small` (244M params): Better accuracy, ~1.5 GB RAM, ~3 GB disk
  - `medium` (769M params): High accuracy, ~3 GB RAM, ~5 GB disk
  - `large` (1550M params): Best accuracy, ~5 GB RAM, ~10 GB disk

  **English-only models (`.en`):**
  Optimized for English-only transcription, slightly faster and more accurate for English.

- **UI Location:** Settings → Models → Model Selector
- **Related Settings:** [Compute Type](#compute-type), [Language](#language)
- **Performance Impact:** Larger models = better accuracy but slower transcription and higher resource usage

### Model Management

#### Download Model

- **Action:** Download button next to each model
- **Description:** Downloads selected Whisper model from Hugging Face Hub to local cache (`~/.cache/huggingface/`)
- **Progress:** Shows download progress bar with percentage and speed
- **Requirements:** Internet connection, sufficient disk space

#### Delete Model

- **Action:** Delete button next to downloaded models
- **Description:** Removes model from local cache to free disk space
- **Warning:** Cannot delete currently selected model (select different model first)

---

## Audio Page

### Microphone

- **Type:** Dropdown selector
- **Default:** System default microphone
- **Options:** All available audio input devices detected by PyAudio
- **Description:**
  Select which microphone to use for recording. Devices are listed by name.

  **Device naming examples:**
  - `Default` - System default microphone
  - `HDA Intel PCH: ALC295 Analog (hw:0,0)` - Built-in laptop microphone
  - `USB Audio Device` - External USB microphone

- **UI Location:** Settings → Audio → Microphone Selector
- **Related Settings:** None
- **Troubleshooting:** If no devices appear, see [Troubleshooting: No audio devices found](../getting-started/troubleshooting.md#no-audio-devices-found)

### Sample Rate Mode

- **Type:** Radio selector
- **Default:** `Whisper (16 kHz)`
- **Options:**
  - **Whisper (16 kHz):** Record at 16 kHz directly (recommended)
  - **Device Native:** Use device's native sample rate, resample to 16 kHz for Whisper

- **Description:**
  Controls audio recording sample rate. Whisper models expect 16 kHz input.

  **Whisper (16 kHz) - Recommended:**
  - Records directly at 16 kHz (Whisper's native rate)
  - No resampling needed, lower CPU usage
  - Smaller in-memory audio buffers
  - Better privacy (lower quality audio)

  **Device Native:**
  - Uses microphone's native sample rate (often 44.1 kHz or 48 kHz)
  - Resamples to 16 kHz before transcription
  - Slightly higher CPU usage
  - May improve quality for some devices

- **UI Location:** Settings → Audio → Sample Rate Mode
- **Related Settings:** None
- **Performance Impact:** Whisper (16 kHz) is more efficient; Device Native adds resampling overhead

---

## Transcription Page

### Language

- **Type:** Dropdown selector
- **Default:** `auto` (automatic detection)
- **Options:** `auto`, `af`, `ar`, `hy`, `az`, `be`, `bs`, `bg`, `ca`, `zh`, `hr`, `cs`, `da`, `nl`, `en`, `et`, `fi`, `fr`, `gl`, `de`, `el`, `he`, `hi`, `hu`, `is`, `id`, `it`, `ja`, `kn`, `kk`, `ko`, `lv`, `lt`, `mk`, `ms`, `mr`, `mi`, `ne`, `no`, `fa`, `pl`, `pt`, `ro`, `ru`, `sr`, `sk`, `sl`, `es`, `sw`, `sv`, `tl`, `ta`, `th`, `tr`, `uk`, `ur`, `vi`, `cy`
- **Description:**
  Language of the speech to transcribe. `auto` detects automatically. Specifying the correct language improves accuracy and speed.

  **Language codes:**
  - `en` - English
  - `es` - Spanish
  - `fr` - French
  - `de` - German
  - `zh` - Chinese
  - `ja` - Japanese
  - (See full list in dropdown)

- **UI Location:** Settings → Transcription → Language
- **Related Settings:** [Selected Model](#selected-model) (use `.en` models for English-only)
- **Performance Impact:** Specifying language is slightly faster than `auto` detection

### Compute Type

- **Type:** Dropdown selector
- **Default:** `auto`
- **Options:**
  - **auto:** Use GPU (CUDA) if available, fallback to CPU (int8)
  - **float32:** CPU, highest quality, slowest
  - **float16:** GPU only (CUDA), high quality, fast
  - **int8:** CPU, quantized, good quality, fastest on CPU

- **Description:**
  Controls precision and hardware for transcription.

  **auto (Recommended):**
  - Detects NVIDIA GPU with CUDA
  - Uses `float16` on GPU or `int8` on CPU
  - Best balance of speed and quality

  **float32:**
  - Full precision, CPU only
  - Highest accuracy but very slow
  - Use for critical accuracy requirements

  **float16:**
  - Half precision, requires NVIDIA GPU with CUDA
  - 2-3x faster than float32 with minimal accuracy loss
  - Recommended for GPU users

  **int8:**
  - 8-bit quantized, CPU optimized
  - Fastest CPU option
  - Minimal accuracy loss vs float32

- **UI Location:** Settings → Transcription → Compute Type
- **Related Settings:** [Selected Model](#selected-model)
- **GPU Requirements:** CUDA toolkit must be installed for GPU acceleration
- **Performance Impact:** GPU (float16) is 5-10x faster than CPU (int8) for larger models

### Beam Size

- **Type:** Spin box (integer)
- **Default:** `5`
- **Range:** 1-10
- **Description:**
  Beam search width for transcription decoding. Higher values may improve accuracy but increase processing time.

  **Recommendations:**
  - `1`: Greedy decoding, fastest but lower accuracy
  - `5`: Good balance (default)
  - `10`: Maximum accuracy, slower

- **UI Location:** Settings → Transcription → Beam Size
- **Related Settings:** None
- **Performance Impact:** Higher beam size = better accuracy but slower transcription (linear increase)

### VAD Filter

- **Type:** Toggle switch
- **Default:** `Enabled`
- **Description:**
  Voice Activity Detection (VAD) filter removes silence from audio before transcription.

  **Enabled (Recommended):**
  - Removes silence and non-speech segments
  - Faster transcription (less audio to process)
  - Better accuracy (Whisper focuses on speech)
  - Useful for recordings with long pauses

  **Disabled:**
  - Processes entire audio including silence
  - Slower transcription
  - May include "..." or artifacts in transcription for silent segments

- **UI Location:** Settings → Transcription → VAD Filter
- **Related Settings:** None
- **Performance Impact:** VAD enabled can significantly speed up transcription for long recordings with pauses

### Word Timestamps

- **Type:** Toggle switch
- **Default:** `Disabled`
- **Description:**
  Generate word-level timestamps during transcription.

  **Disabled (Default):**
  - Returns only transcription text
  - Faster processing

  **Enabled:**
  - Returns text with word-level timing information
  - Slower processing (20-30% overhead)
  - Currently timestamps are logged but not shown in UI (future feature)

- **UI Location:** Settings → Transcription → Word Timestamps
- **Related Settings:** None
- **Performance Impact:** Enabling adds ~20-30% processing time
- **Note:** Timestamps are currently for debugging; no UI display yet

---

## Shortcuts Page

### Toggle Recording Shortcut

- **Type:** Key combination selector
- **Default:** `Alt+Space`
- **Description:**
  Global keyboard shortcut to start/stop recording. Works system-wide even when Syllablaze is not focused.

  **Behavior:**
  - **Idle state:** Press to start recording
  - **Recording state:** Press to stop recording and begin transcription
  - **Transcribing state:** Shortcut ignored (wait for transcription to complete)

- **UI Location:** Settings → Shortcuts → Toggle Recording
- **Supported Modifiers:** `Ctrl`, `Alt`, `Shift`, `Meta` (Super/Windows key)
- **Example Combinations:** `Alt+Space`, `Ctrl+Alt+R`, `Meta+T`
- **Conflicts:** If shortcut is already used by another application, it may not work reliably
- **Platform Support:**
  - **KDE Wayland:** Uses KGlobalAccel D-Bus API (native integration)
  - **X11:** Uses pynput keyboard listener (requires X11 permissions)
  - **Other DEs:** Uses pynput (may require accessibility permissions)

### Re-register Shortcut

- **Action:** Re-register button
- **Description:** Re-registers the global shortcut with the system. Use if shortcut stops working after system changes or conflicts.

---

## UI Page

Visual indicators and window behavior settings.

### Popup Style

- **Type:** Visual 3-card radio selector
- **Default:** `Applet`
- **Options:**
  - **None:** No visual indicator during recording
  - **Traditional:** Progress bar window (classic UI, 280x160px)
  - **Applet:** Circular waveform dialog with volume visualization

- **Description:**
  Controls which visual indicator appears during recording and transcription.

  **None:**
  - No visual feedback
  - Use tray icon to monitor status
  - Minimal distraction
  - Clipboard notification only

  **Traditional:**
  - Classic progress bar window
  - Shows "Recording..." or "Transcribing..." text
  - Progress bar for transcription
  - Always on top option available
  - Suitable for users who prefer traditional UI

  **Applet:**
  - Modern circular dialog with real-time waveform
  - Volume visualization (green → yellow → red)
  - Interactive: click to toggle recording, drag to move, scroll to resize
  - Right-click context menu
  - Configurable auto-hide behavior
  - Suitable for KDE Plasma users

- **UI Location:** Settings → UI → Popup Style (top section with visual cards)
- **Related Settings:**
  - [Applet Auto-hide](#applet-auto-hide) (when Applet selected)
  - [Always on Top](#always-on-top-traditional-window) (when Traditional selected)

- **Backend Mapping:** See [Settings Architecture](../explanation/settings-architecture.md) for how this maps to backend settings

### Applet Auto-hide

- **Type:** Toggle switch
- **Default:** `Enabled`
- **Visible When:** Popup Style = Applet
- **Description:**
  Controls recording dialog visibility behavior.

  **Enabled (Popup Mode):**
  - Dialog auto-shows when recording starts
  - Dialog auto-hides 500ms after transcription completes
  - Minimal screen occupation
  - Can manually dismiss via right-click menu

  **Disabled (Persistent Mode):**
  - Dialog always visible (even when idle)
  - Click to toggle recording on/off
  - Persistent visual indicator
  - Useful for frequent recordings

- **UI Location:** Settings → UI → Applet Options (below Applet card when selected)
- **Related Settings:** [Popup Style](#popup-style) must be Applet
- **Backend Mapping:**
  - Enabled → `applet_mode=popup`
  - Disabled → `applet_mode=persistent`

### Dialog Size

- **Type:** Spin box (integer)
- **Default:** `200` pixels
- **Range:** 100-500 pixels
- **Visible When:** Popup Style = Applet
- **Description:**
  Size of the circular recording dialog in pixels (diameter).

  **Recommendations:**
  - `100-150`: Small, minimal distraction
  - `200`: Default, good visibility
  - `300-500`: Large, easier to interact with

- **UI Location:** Settings → UI → Applet Options → Dialog Size
- **Related Settings:** [Popup Style](#popup-style) must be Applet
- **Runtime Resize:** You can also resize by scrolling mouse wheel over the dialog

### Always on Top (Applet)

- **Type:** Toggle switch
- **Default:** `Enabled`
- **Visible When:** Popup Style = Applet
- **Description:**
  Keeps recording dialog above other windows.

  **Enabled:**
  - Dialog stays on top of all other windows
  - Prevents accidental occlusion
  - Uses KWin window rules for persistence

  **Disabled:**
  - Dialog behaves like normal window
  - Can be covered by other windows

- **UI Location:** Settings → UI → Applet Options → Always on top
- **Related Settings:** [Popup Style](#popup-style) must be Applet
- **Wayland Note:** May require restart or toggle off/on to take effect. See [Troubleshooting: Always-on-top requires restart](../getting-started/troubleshooting.md#always-on-top-requires-restart)

### Always on Top (Traditional Window)

- **Type:** Toggle switch
- **Default:** `Enabled`
- **Visible When:** Popup Style = Traditional
- **Description:**
  Keeps traditional progress window above other windows.

- **UI Location:** Settings → UI → Traditional Window Options → Always on top
- **Related Settings:** [Popup Style](#popup-style) must be Traditional
- **Wayland Note:** May require restart to take effect

### Show on All Desktops

- **Type:** Toggle switch
- **Default:** `Disabled`
- **Visible When:** Popup Style = Applet
- **Description:**
  Shows recording dialog on all virtual desktops.

  **Enabled:**
  - Dialog visible on every virtual desktop
  - No need to switch desktops to see recording status
  - Uses KWin D-Bus API

  **Disabled:**
  - Dialog appears only on desktop where recording started
  - May disappear when switching virtual desktops

- **UI Location:** Settings → UI → Applet Options → Show on all desktops
- **Related Settings:** [Popup Style](#popup-style) must be Applet
- **Platform:** KDE Plasma only (requires KWin)

---

## About Page

### Application Version

- **Type:** Display only
- **Description:** Shows current Syllablaze version (e.g., `v0.5`)

### Debug Logging

- **Type:** Toggle switch
- **Default:** `Disabled`
- **Description:**
  Enables detailed debug logging for troubleshooting.

  **Disabled:**
  - Logs only warnings and errors
  - Minimal log file size

  **Enabled:**
  - Logs detailed debug information
  - Useful for troubleshooting issues
  - Larger log file size

- **UI Location:** Settings → About → Enable Debug Logging
- **Log Location:** `~/.local/state/syllablaze/syllablaze.log`
- **Viewing Logs:**
  ```bash
  tail -100 ~/.local/state/syllablaze/syllablaze.log
  tail -f ~/.local/state/syllablaze/syllablaze.log  # Follow in real-time
  ```

### Credits and Links

- **Repository:** Link to GitHub repository
- **License:** MIT License
- **About:** Project description and credits

---

## Backend Settings (Advanced)

These settings are derived automatically from high-level UI settings and are not directly exposed in the UI. They are documented here for developers and advanced users.

### show_recording_dialog

- **Type:** Boolean (internal)
- **Derived From:** [Popup Style](#popup-style)
- **Mapping:**
  - `Popup Style = None` → `False`
  - `Popup Style = Traditional` → `False`
  - `Popup Style = Applet` → `True`

### show_progress_window

- **Type:** Boolean (internal)
- **Derived From:** [Popup Style](#popup-style)
- **Mapping:**
  - `Popup Style = None` → `False`
  - `Popup Style = Traditional` → `True`
  - `Popup Style = Applet` → `False`

### applet_mode

- **Type:** String (internal)
- **Derived From:** [Popup Style](#popup-style) + [Applet Auto-hide](#applet-auto-hide)
- **Values:** `off`, `popup`, `persistent`
- **Mapping:**
  - `Popup Style = None` → `off`
  - `Popup Style = Traditional` → `off`
  - `Popup Style = Applet` + `Applet Auto-hide = On` → `popup`
  - `Popup Style = Applet` + `Applet Auto-hide = Off` → `persistent`

**Reference:** See [Settings Architecture](../explanation/settings-architecture.md) for detailed derivation logic.

---

## Settings Storage

Settings are stored using Qt's `QSettings`:

- **Location (Linux):** `~/.config/Syllablaze/Syllablaze.conf`
- **Format:** INI-style configuration file
- **Persistence:** Settings persist across application restarts
- **Reset:** Delete config file to reset all settings to defaults

---

## Related Documentation

- **[Recording Modes Explained](recording-modes.md)** - Visual guide to None/Traditional/Applet modes
- **[Settings Architecture](../explanation/settings-architecture.md)** - How settings derivation works
- **[Troubleshooting](../getting-started/troubleshooting.md)** - Common settings-related issues
