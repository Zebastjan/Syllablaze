# Recording Modes

Syllablaze offers three recording indicator modes to suit different preferences and workflows. Choose the mode that best fits your usage pattern in Settings → UI → Popup Style.

## Visual Comparison

| Feature | None | Traditional | Applet |
|---------|------|-------------|--------|
| **Visual indicator** | None | Progress window | Circular waveform |
| **Screen occupation** | Minimal | Medium | Small |
| **Interactivity** | Tray only | View only | Fully interactive |
| **Volume feedback** | No | No | Yes (real-time) |
| **Auto-hide** | N/A | No | Optional |
| **Always on top** | N/A | Optional | Optional |

## None Mode

**Best for:** Users who want zero visual distraction and monitor status via tray icon only.

**Behavior:**
- No window appears during recording or transcription
- Tray icon changes color/tooltip to show status
- Notification after transcription completes
- Clipboard automatically receives transcription

**Advantages:**
- Zero screen occupation
- Maximum focus
- Minimal resource usage

**Disadvantages:**
- No visual feedback during recording
- Must watch tray icon for status
- No volume monitoring

**Recommended for:** Experienced users, frequent short recordings, minimal distraction preference.

## Traditional Mode

**Best for:** Users who prefer classic progress bar UI and don't need interactivity.

**Behavior:**
- Progress window appears when recording starts
- Shows "Recording..." text during capture
- Shows "Transcribing..." with progress bar during processing
- Window auto-closes after transcription
- Always on top option available

**Window size:** 280x160 pixels (half of original size for unobtrusiveness)

**Advantages:**
- Clear status indication
- Progress tracking during transcription
- Familiar UI pattern
- No learning curve

**Disadvantages:**
- Occupies screen space
- Not interactive (can't click to stop)
- No volume visualization

**Recommended for:** Users migrating from other transcription apps, those who prefer traditional UIs.

## Applet Mode (Recommended)

**Best for:** Users who want real-time feedback, interactivity, and modern KDE integration.

**Behavior:**
- Circular window with radial waveform visualization
- Volume bars animate in real-time (green → yellow → red as volume increases)
- Two sub-modes:
  - **Auto-hide (default):** Dialog auto-shows on recording start, auto-hides 500ms after transcription
  - **Persistent:** Dialog always visible (even when idle)

**Interactive Features:**
- **Left-click:** Toggle recording on/off
- **Double-click:** Dismiss dialog
- **Right-click:** Context menu (Start/Stop, Clipboard, Settings, Dismiss)
- **Middle-click:** Open clipboard manager
- **Drag:** Reposition window anywhere on screen
- **Scroll wheel:** Resize (100-500px range)

**Customization:**
- Dialog size: 100-500 pixels (default: 200)
- Always on top: Keep above other windows
- Show on all desktops: Visible on every virtual desktop (KDE only)

**Advantages:**
- Real-time volume feedback
- Fully interactive (no need to use tray)
- Modern, KDE-native appearance
- Highly customizable
- Auto-hide reduces distraction

**Disadvantages:**
- Slightly higher resource usage (real-time rendering)
- Requires learning interaction gestures
- Position doesn't persist on Wayland

**Recommended for:** KDE Plasma users, those who want visual feedback, interactive control preference.

## Choosing the Right Mode

### Use None if:
- You want zero visual distraction
- You record very frequently (dozens per day)
- Screen space is at premium
- You're comfortable monitoring tray icon

### Use Traditional if:
- You prefer classic UI patterns
- You want progress tracking
- Interactivity isn't important
- You're migrating from other apps

### Use Applet if:
- You use KDE Plasma (best integration)
- You want real-time volume visualization
- You prefer interactive controls
- You like modern, circular design

## Switching Modes

Settings → UI → Popup Style → Select None/Traditional/Applet

**Changes take effect immediately** (no restart required).

## Technical Details

### None Mode Implementation
- No UI components instantiated
- Minimal memory footprint
- Status updates via tray icon tooltip and color

### Traditional Mode Implementation
- QtWidgets `ProgressWindow` with progress bar
- Shows on recording start, hides on completion
- Always-on-top uses Qt window flags

### Applet Mode Implementation
- QML `RecordingDialog.qml` with Canvas-based waveform
- Real-time audio level updates via `RecordingDialogBridge`
- SVG-based circular background
- 36 radial bars with color gradient (green/yellow/red)
- Debounced position/size persistence (500ms)

See [Design Decisions](../explanation/design-decisions.md) for architectural details.

---

**Related Documentation:**
- [Settings Reference](settings-reference.md) - All popup style settings
- [Features Overview](features.md) - All Syllablaze features
- [Design Decisions: UI/UX](../explanation/design-decisions.md#uiux-decisions)
