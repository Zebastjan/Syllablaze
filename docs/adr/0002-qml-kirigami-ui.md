# ADR-0002: QML UI with Kirigami Framework

**Status:** Accepted
**Date:** 2026-02-19
**Deciders:** Developer

## Context

Syllablaze's original settings window was built with QtWidgets (`QDialog`, `QVBoxLayout`, `QCheckBox`, etc.). While functional, it had several UX problems:

- **Visual mismatch:** Didn't match KDE Plasma's modern Kirigami styling
- **Non-native appearance:** Looked like a generic Qt application, not a KDE app
- **Limited responsiveness:** Fixed layouts didn't adapt well to different screen sizes
- **Poor high-DPI support:** Scaling issues on 4K displays
- **Maintenance burden:** QtWidgets requires manual layout management
- **Inconsistent with KDE ecosystem:** Other KDE apps use Kirigami (Dolphin, Konsole, etc.)

The recording dialog also used QtWidgets initially, with similar styling inconsistencies. As a KDE Plasma-focused application, Syllablaze should integrate natively with the desktop environment.

**Requirements:**
- Match KDE Plasma's visual style (Breeze theme, Kirigami components)
- Support high-DPI displays automatically
- Provide responsive layouts that adapt to window size
- Reduce boilerplate UI code
- Enable rapid UI iteration

**Constraints:**
- Must maintain Python backend (PyQt6)
- Cannot require Qt Designer or additional tooling
- Settings must persist (QSettings integration)
- Must support both X11 and Wayland

## Decision

Migrate UI components to **QML with Kirigami framework**:

1. **Settings window:** Complete rewrite using Kirigami `ApplicationWindow` and `FormLayout`
2. **Recording dialog:** Migrate to QML with custom `Canvas` for visualization
3. **Python-QML bridge:** Create `SettingsBridge`, `RecordingDialogBridge`, `ActionsBridge` for bidirectional communication
4. **Keep traditional windows as QtWidgets:** ProgressWindow, LoadingWindow remain QtWidgets (simple, no Kirigami benefit)

### QML Pages Structure

```
blaze/qml/
├── SyllablazeSettings.qml         # Main window (Kirigami.ApplicationWindow)
├── RecordingDialog.qml             # Circular waveform applet
└── pages/
    ├── ModelsPage.qml              # Model selection and management
    ├── AudioPage.qml               # Microphone and sample rate
    ├── TranscriptionPage.qml       # Language, compute type, VAD
    ├── ShortcutsPage.qml           # Global keyboard shortcuts
    ├── UIPage.qml                  # Visual indicators (popup style)
    └── AboutPage.qml               # Version, credits, debug logging
```

### Python-QML Bridges

**SettingsBridge** (`blaze/kirigami_integration.py`):
```python
class SettingsBridge(QObject):
    settingChanged = pyqtSignal(str, 'QVariant')

    @pyqtSlot(str, result='QVariant')
    def get(self, key):
        return self.settings.get(key)

    @pyqtSlot(str, 'QVariant')
    def set(self, key, value):
        self.settings.set(key, value)
        self.settingChanged.emit(key, value)
```

**RecordingDialogBridge** (`blaze/recording_dialog_manager.py`):
- Exposes `isRecording`, `volume`, `dialogSize` as pyqtProperty
- Provides slots for `toggleRecording()`, `dismissDialog()`
- Emits signals for state changes

**ActionsBridge** (`blaze/kirigami_integration.py`):
- Provides slots for user actions: `openURL()`, `openSystemSettings()`
- Separates actions from settings for cleaner architecture

### Visual Improvements

**Before (QtWidgets):**
- Generic checkbox lists
- Plain dropdowns
- Flat buttons
- No visual feedback
- Fixed spacing

**After (QML + Kirigami):**
- Kirigami `FormLayout` with proper labels and spacing
- `ComboBox` with Breeze styling
- `Button` with hover/press animations
- Visual 3-card radio selector for popup style (None/Traditional/Applet)
- Conditional visibility for related settings
- Adaptive layouts for different screen sizes
- Automatic high-DPI scaling via `devicePixelRatio`

## Consequences

### Positive

- **Native KDE look:** Matches Plasma desktop styling perfectly
- **Better UX:** Kirigami components provide better visual feedback
- **Declarative UI:** QML is more concise than QtWidgets manual layouts
- **Responsive:** Layouts adapt to window size automatically
- **High-DPI support:** Qt handles scaling via device pixel ratio
- **Rapid iteration:** UI changes don't require Python recompilation
- **Component reuse:** QML components can be reused across pages
- **Animation support:** Kirigami provides smooth transitions out-of-box
- **Accessibility:** Kirigami components have better keyboard navigation

### Negative

- **Python-QML bridge complexity:** Requires careful signal/slot/property design
- **Debugging difficulty:** QML errors sometimes cryptic, runtime-only checking
- **Two languages:** Developers must know both Python and QML
- **Load time:** QML engine initialization adds ~100-200ms startup time
- **Documentation:** Kirigami docs less comprehensive than QtWidgets
- **Type safety:** QML is dynamically typed, type errors only at runtime

### Neutral

- **File organization:** QML files separate from Python (clearer structure)
- **Build process:** No additional build steps (QML loaded at runtime)
- **Dependencies:** Kirigami is part of KDE Frameworks (already available on KDE)

## Alternatives Considered

### Alternative 1: Continue with QtWidgets

- **Description:** Improve existing QtWidgets UI with custom styling
- **Pros:** No migration needed, one language (Python), simpler debugging
- **Cons:** Never matches Kirigami styling, manual layout management, poor high-DPI
- **Reason for rejection:** Doesn't solve core UX problems, technical debt grows

### Alternative 2: GTK+ (Python + GTK3/4)

- **Description:** Switch to GTK for native GNOME styling
- **Pros:** Mature Python bindings, good documentation, declarative via GtkBuilder
- **Cons:** Wrong ecosystem for KDE Plasma users, doesn't match Breeze theme
- **Reason for rejection:** Syllablaze targets KDE Plasma specifically

### Alternative 3: Web Technologies (Electron, Qt WebEngine)

- **Description:** Embed HTML/CSS/JavaScript UI in Qt WebEngine or Electron
- **Pros:** Web dev skills reusable, rich ecosystem (React, Vue, etc.)
- **Cons:** Massive overhead (100+ MB bundle), poor integration, high memory usage
- **Reason for rejection:** Over-engineering for simple settings window

### Alternative 4: Pure QML (no Kirigami)

- **Description:** Use QtQuick QML components without Kirigami
- **Pros:** Lighter weight, fewer dependencies, more control
- **Cons:** Doesn't match KDE styling, need to reimplement Kirigami components
- **Reason for rejection:** Kirigami exists specifically for KDE integration

## References

- **Code:** `blaze/kirigami_integration.py`, `blaze/qml/`, `blaze/recording_dialog_manager.py`
- **Documentation:** [Patterns & Pitfalls](../developer-guide/patterns-and-pitfalls.md#qml-python-bridges)
- **Archive:** `docs/archive/migrations/KIRIGAMI_MIGRATION.md` (original migration plan)
- **External:**
  - [Kirigami Documentation](https://develop.kde.org/frameworks/kirigami/)
  - [Qt QML Documentation](https://doc.qt.io/qt-6/qtqml-index.html)
  - [PyQt6 QML Integration](https://www.riverbankcomputing.com/static/Docs/PyQt6/qml.html)
- **Related ADRs:** None

---

**Implementation notes:**
- QML files use Kirigami 2.20+ components
- Python bridges inherit from `QObject` and use `pyqtSignal`/`pyqtSlot`/`pyqtProperty`
- Settings changes flow: QML → SettingsBridge.set() → Settings.set() → SettingsBridge.settingChanged signal → SettingsCoordinator
- SVG assets loaded via `SvgRendererBridge.svgPath` property (for Applet preview card)
- Recording dialog uses QML `Canvas` with JavaScript for radial waveform visualization
- Traditional progress window remains QtWidgets (no Kirigami benefit for simple window)
