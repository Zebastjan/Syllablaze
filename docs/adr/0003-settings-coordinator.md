# ADR-0003: Settings Coordinator Pattern

**Status:** Accepted
**Date:** 2026-02-19
**Deciders:** Agent + Developer

## Context

Syllablaze has two types of settings:

**User-facing settings (high-level UX):**
- `popup_style`: None / Traditional / Applet (visual 3-card selector in UI)
- `applet_autohide`: Boolean toggle for auto-hide behavior

**Backend settings (implementation details):**
- `show_recording_dialog`: Show QML recording dialog?
- `show_progress_window`: Show traditional progress window?
- `applet_mode`: `off` / `popup` / `persistent` (controls auto-show/hide logic)

**The problem:**

Exposing all backend settings directly in the UI creates confusion:
- Users don't understand the difference between `show_recording_dialog` and `show_progress_window`
- Three backend settings for what users think of as one choice (which visual indicator?)
- Contradictory states possible (both dialog and progress window enabled)
- Backend details leak into UX layer

Hardcoding the relationship creates rigidity:
- Can't change backend implementation without updating UI
- Difficult to add new modes (would require UI changes)
- Testing requires manipulating low-level settings

**Requirements:**
- Simple user-facing UI with clear choices
- Flexible backend settings for implementation details
- Centralized derivation logic to prevent inconsistencies
- Ability to evolve backend without breaking UI

**Constraints:**
- Existing backend code expects `show_recording_dialog`, `show_progress_window`, `applet_mode`
- Settings must persist across app restarts
- Components listen to settings changes via signals
- Wayland-specific window visibility coordination requires `applet_mode` values

## Decision

Introduce **SettingsCoordinator** to derive backend settings from high-level user settings.

### High-Level to Backend Mapping

| popup_style | applet_autohide | show_progress_window | show_recording_dialog | applet_mode |
|-------------|-----------------|----------------------|-----------------------|-------------|
| none        | —               | False                | False                 | off         |
| traditional | —               | True                 | False                 | off         |
| applet      | True            | False                | True                  | popup       |
| applet      | False           | False                | True                  | persistent  |

### SettingsCoordinator Implementation

```python
class SettingsCoordinator:
    def __init__(self, settings):
        self.settings = settings
        settings.settingChanged.connect(self.on_setting_changed)

    def on_setting_changed(self, key, value):
        if key in ('popup_style', 'applet_autohide'):
            self._apply_popup_style()
        # ... other coordinations

    def _apply_popup_style(self):
        popup_style = self.settings.get('popup_style', 'applet')
        autohide = self.settings.get('applet_autohide', True)

        # Derive backend settings from high-level choice
        if popup_style == 'none':
            self.settings.set('show_progress_window', False)
            self.settings.set('show_recording_dialog', False)
            self.settings.set('applet_mode', 'off')
        elif popup_style == 'traditional':
            self.settings.set('show_progress_window', True)
            self.settings.set('show_recording_dialog', False)
            self.settings.set('applet_mode', 'off')
        elif popup_style == 'applet':
            self.settings.set('show_progress_window', False)
            self.settings.set('show_recording_dialog', True)
            self.settings.set('applet_mode', 'popup' if autohide else 'persistent')
```

### Component Integration

**UIPage.qml (QML):**
```qml
// User sees simple 3-card selector
RadioButton {
    text: "Applet"
    checked: settingsBridge.get("popup_style") === "applet"
    onCheckedChanged: settingsBridge.set("popup_style", "applet")
}

// Conditional sub-option
CheckBox {
    text: "Auto-hide when idle"
    visible: settingsBridge.get("popup_style") === "applet"
    checked: settingsBridge.get("applet_autohide")
    onCheckedChanged: settingsBridge.set("applet_autohide", checked)
}
```

**WindowVisibilityCoordinator (Python):**
```python
# Backend reads derived settings
applet_mode = self.settings.get('applet_mode')
if applet_mode == 'popup':
    # Auto-show on recording start, auto-hide after transcription
    app_state.recording_started.connect(self._auto_show)
elif applet_mode == 'persistent':
    # Keep visible always
    self._ensure_visible()
```

### Flow Diagram

```
User selects "Applet" + Auto-hide OFF in UI
  ↓
UIPage.qml: settingsBridge.set("popup_style", "applet")
             settingsBridge.set("applet_autohide", false)
  ↓
Settings.set() validates and writes to QSettings
  ↓
Settings.settingChanged signal emitted
  ↓
SettingsCoordinator.on_setting_changed() triggered
  ↓
SettingsCoordinator._apply_popup_style() derives backend settings:
  - show_progress_window = False
  - show_recording_dialog = True
  - applet_mode = "persistent"
  ↓
Settings.set() called for each derived setting
  ↓
Settings.settingChanged emitted for each
  ↓
Components (UIManager, WindowVisibilityCoordinator) react to backend changes
```

## Consequences

### Positive

- **Simplified UX:** Users see clear, meaningful choices (None/Traditional/Applet)
- **Centralized logic:** Derivation in one place, easy to understand and test
- **Flexibility:** Backend can evolve without UI changes
- **Consistency:** Impossible to create contradictory backend states
- **Testability:** Can unit test derivation logic independently
- **Extensibility:** Easy to add new popup styles (just update mapping table)
- **Documentation:** Mapping table clearly documents relationships

### Negative

- **Indirection:** Must trace through SettingsCoordinator to understand backend values
- **Signal complexity:** Multiple settingChanged signals fired for one user action
- **Debugging:** More components involved in settings flow
- **Backward compatibility:** Must maintain old backend settings for existing code

### Neutral

- **Settings storage:** Both high-level and backend settings persisted (redundant but harmless)
- **Migration:** Existing users have backend settings; coordinator derives correctly on first run

## Alternatives Considered

### Alternative 1: Direct Backend Exposure

- **Description:** Expose `show_recording_dialog`, `show_progress_window`, `applet_mode` directly in UI
- **Pros:** Simple, no derivation needed, direct control
- **Cons:** Confusing UX, contradictory states possible, implementation details leak
- **Reason for rejection:** Poor user experience, prone to user error

### Alternative 2: Hardcoded Mapping in UI

- **Description:** UIPage.qml directly sets all three backend settings when popup_style changes
- **Pros:** No coordinator needed, simpler architecture
- **Cons:** Derivation logic in QML (hard to test), duplicated if multiple UI entry points
- **Reason for rejection:** Logic belongs in Python (testable), not QML

### Alternative 3: Only Store High-Level Settings

- **Description:** Delete backend settings, derive on-the-fly when needed
- **Pros:** Single source of truth, no redundancy
- **Cons:** Components must call derivation function each time, can't listen to specific backend changes
- **Reason for rejection:** Breaks existing signal-based architecture

### Alternative 4: Settings Profiles

- **Description:** Predefined profiles (e.g., "Minimal", "Standard", "Full") set all settings
- **Pros:** Even simpler UX, opinionated defaults
- **Cons:** Less flexibility, users can't mix-and-match, more profiles needed for edge cases
- **Reason for rejection:** Too restrictive, Syllablaze users want granular control

## References

- **Code:** `blaze/managers/settings_coordinator.py`, `blaze/qml/pages/UIPage.qml`
- **Documentation:**
  - [Settings Architecture](../explanation/settings-architecture.md)
  - [Settings Reference](../user-guide/settings-reference.md#backend-settings-advanced)
- **Related ADRs:**
  - [ADR-0001: Manager Pattern](0001-manager-pattern.md) (SettingsCoordinator is a manager)
  - [ADR-0002: QML Kirigami UI](0002-qml-kirigami-ui.md) (UIPage.qml uses SettingsBridge)
- **Archive:** `docs/archive/implementation-summaries/` (refactoring notes)

---

**Implementation notes:**
- SettingsCoordinator initialized in `SyllablazeOrchestrator.__init__()`
- Derivation triggered by `settingChanged` signal from Settings
- Backend settings (`show_*`, `applet_mode`) are **derived values**, not primary settings
- Old backend settings kept for backward compatibility with existing components
- CLAUDE.md documents this pattern for agent reference (see "Settings Architecture" section)
- Future: Could add validation to prevent direct backend setting changes bypassing coordinator
