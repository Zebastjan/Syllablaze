# Settings Architecture

Detailed explanation of Syllablaze's settings derivation pattern. For the decision rationale, see [ADR-0003: Settings Coordinator](../adr/0003-settings-coordinator.md).

## Problem: Two Types of Settings

Syllablaze has two categories of settings:

**User-Facing (High-Level UX):**
- Simple choices users understand
- Example: "Which visual indicator do you want?" → None / Traditional / Applet

**Backend (Implementation Details):**
- Technical settings components need
- Example: `show_progress_window`, `show_recording_dialog`, `applet_mode`

**Challenge:** Exposing backend settings confuses users. Hardcoding mapping is inflexible.

## Solution: SettingsCoordinator

The `SettingsCoordinator` derives backend settings from high-level user choices.

### Derivation Table

| popup_style | applet_autohide | show_progress_window | show_recording_dialog | applet_mode |
|-------------|-----------------|----------------------|-----------------------|-------------|
| none        | —               | False                | False                 | off         |
| traditional | —               | True                 | False                 | off         |
| applet      | True            | False                | True                  | popup       |
| applet      | False           | False                | True                  | persistent  |

### Implementation

**File:** `blaze/managers/settings_coordinator.py`

```python
class SettingsCoordinator:
    def on_setting_changed(self, key, value):
        if key in ('popup_style', 'applet_autohide'):
            self._apply_popup_style()

    def _apply_popup_style(self):
        popup_style = self.settings.get('popup_style', 'applet')
        autohide = self.settings.get('applet_autohide', True)

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
            mode = 'popup' if autohide else 'persistent'
            self.settings.set('applet_mode', mode)
```

## Data Flow

```
User selects "Applet" + Auto-hide OFF in Settings UI
  ↓
UIPage.qml: settingsBridge.set("popup_style", "applet")
            settingsBridge.set("applet_autohide", false)
  ↓
Settings.set() validates and writes to QSettings
  ↓
Settings.settingChanged signal emitted (twice)
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
Settings.settingChanged emitted for backend changes
  ↓
Components (UIManager, WindowVisibilityCoordinator) react
```

## Why This Works

### Simplified UX
- Users see 3 visual cards: None / Traditional / Applet
- Sub-option appears conditionally: "Auto-hide when idle"
- No technical jargon like "applet_mode" or "show_recording_dialog"

### Centralized Logic
- Derivation in one place: `SettingsCoordinator._apply_popup_style()`
- Easy to test: Unit test derivation independently
- Clear mapping: Table documents relationships

### Backend Flexibility
- Components continue using backend settings unchanged
- `UIManager` reads `show_progress_window`
- `WindowVisibilityCoordinator` reads `applet_mode`
- No component changes required

### Extensibility
- Add new popup style: Update derivation table
- Change backend implementation: Modify coordinator only
- UI stays simple regardless of backend complexity

## Settings Storage

### What Gets Persisted

**Both high-level AND backend settings** are written to QSettings:

```ini
# ~/.config/Syllablaze/Syllablaze.conf
[General]
popup_style=applet
applet_autohide=true
show_progress_window=false
show_recording_dialog=true
applet_mode=popup
```

**Redundancy is intentional:**
- Backend settings derived from high-level on every change
- On app restart, coordinator re-derives to ensure consistency
- If user manually edits config file, coordinator fixes inconsistencies

### Migration

On first run after upgrade:
- Old users have only backend settings
- Coordinator reads backend settings and infers high-level setting
- Both are then persisted going forward

## Component Integration

### UIPage.qml (QML UI)

Visual 3-card selector with conditional sub-options:

```qml
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

### WindowVisibilityCoordinator (Backend)

Reads derived `applet_mode`:

```python
applet_mode = self.settings.get('applet_mode')
if applet_mode == 'popup':
    # Auto-show on recording start
    app_state.recording_started.connect(self._auto_show)
    # Auto-hide 500ms after transcription
    app_state.transcription_completed.connect(self._auto_hide_delayed)
elif applet_mode == 'persistent':
    # Keep visible always
    self._ensure_visible()
elif applet_mode == 'off':
    # Never auto-show
    pass
```

## Testing

**Unit test derivation logic:**

```python
def test_apply_popup_style_applet_autohide():
    settings.set('popup_style', 'applet')
    settings.set('applet_autohide', True)
    coordinator._apply_popup_style()

    assert settings.get('show_progress_window') == False
    assert settings.get('show_recording_dialog') == True
    assert settings.get('applet_mode') == 'popup'
```

## Future Extensions

Easily add new popup style:

1. Add to `constants.py`: `POPUP_STYLE_COMPACT = "compact"`
2. Update `Settings.VALID_POPUP_STYLES`
3. Add card to `UIPage.qml`
4. Add derivation case to `SettingsCoordinator._apply_popup_style()`
5. Update documentation

**No component changes required** - backend settings handle implementation.

---

**Related Documentation:**
- [ADR-0003: Settings Coordinator](../adr/0003-settings-coordinator.md) - Decision rationale
- [Settings Reference](../user-guide/settings-reference.md) - All settings explained
- [Design Decisions](design-decisions.md#settings-coordinator) - High-level overview
