# Testing Guide: Applet Interaction Fixes

## Prerequisites

1. **Kill existing Syllablaze instance:**
   ```bash
   pkill syllablaze
   ```

2. **Start Syllablaze with logging:**
   ```bash
   python3 -m blaze.main 2>&1 | tee syllablaze-test.log
   ```

3. **Have a second terminal ready for checking logs:**
   ```bash
   tail -f syllablaze-test.log
   ```

---

## Test 1: Tray Menu "Open/Close Applet" Toggle

### Expected Behavior
- Tray menu item should toggle between "Open Applet" and "Close Applet"
- Clicking should switch between persistent (always visible) and popup (auto-show/hide) modes
- Window should actually show/hide, not just change settings

### Test Steps

1. **Initial State Check:**
   - Right-click tray icon
   - Note the menu item text (should be "Open Applet" if in popup mode, "Close Applet" if persistent)

2. **Test Toggle to Persistent:**
   - Click "Open Applet"
   - ✅ Applet window should appear
   - ✅ Menu item should now say "Close Applet"
   - Check logs for:
     ```
     Tray menu toggling applet mode: autohide True → False (persistent mode)
     Manually triggering settings coordinator for applet_autohide change
     ```

3. **Test Toggle to Popup:**
   - Click "Close Applet"
   - ✅ Applet window should hide
   - ✅ Menu item should now say "Open Applet"
   - Check logs for:
     ```
     Tray menu toggling applet mode: autohide False → True (popup mode)
     Manually triggering settings coordinator for applet_autohide change
     ```

4. **Verify Mode Persists:**
   - Start recording (Alt+Space or tray menu)
   - In popup mode: applet should auto-show
   - In persistent mode: applet should already be visible
   - Stop recording
   - In popup mode: applet should auto-hide after 500ms
   - In persistent mode: applet should stay visible

### Success Criteria
- [x] Menu item text updates correctly
- [x] Applet shows/hides as expected
- [x] Settings coordinator is triggered (check logs)
- [x] Mode behavior works correctly during recording

---

## Test 2: Klipper Clipboard Integration

### Expected Behavior
- Middle-click or "Open Clipboard" menu should open Klipper history
- If Klipper unavailable, show fallback dialog with clipboard content
- All attempts should be logged

### Test Steps

1. **Test Middle-Click (Klipper Running):**
   - Middle-click on applet
   - ✅ Klipper history popup should appear
   - Check logs for:
     ```
     Attempting to open Klipper clipboard history...
     Successfully opened Klipper via: qdbus showKlipperManuallyInvokeActionMenu
     ```

2. **Test Right-Click Menu (Klipper Running):**
   - Right-click on applet
   - Click "Open Clipboard"
   - ✅ Klipper history popup should appear
   - Check logs for same success message

3. **Test Fallback (Klipper Not Running):**
   - Kill Klipper: `pkill klipper`
   - Middle-click on applet
   - ✅ Should show QMessageBox with clipboard content
   - ✅ Dialog should say "Klipper clipboard manager could not be opened via D-Bus"
   - Check logs for:
     ```
     Command failed (exit ...): ...
     Command not found: qdbus6
     All Klipper D-Bus methods failed, showing basic clipboard fallback
     ```

4. **Restart Klipper:**
   - `klipper &`
   - Verify middle-click works again

### Success Criteria
- [x] Middle-click opens Klipper when running
- [x] Menu item opens Klipper when running
- [x] Fallback dialog appears when Klipper unavailable
- [x] Detailed logging shows all D-Bus attempts

---

## Test 3: Clipboard First Use (Wayland Fix)

### Expected Behavior
- Clipboard should work immediately on first transcription after fresh start
- No need to toggle settings or restart

### Test Steps

1. **Fresh Start:**
   ```bash
   pkill syllablaze
   python3 -m blaze.main 2>&1 | tee clipboard-test.log
   ```

2. **First Transcription:**
   - Wait for app to fully initialize (check tray icon appears)
   - Start recording (Alt+Space)
   - Say something: "This is a test transcription"
   - Stop recording
   - Wait for transcription to complete

3. **Verify Clipboard:**
   - Open any text editor
   - Paste (Ctrl+V)
   - ✅ Transcribed text should appear immediately
   - ✅ No need to open settings first

4. **Check Logs:**
   - Look for:
     ```
     ClipboardManager: Initialized with persistent clipboard owner (mapped for Wayland)
     Copied transcription to clipboard: This is a test...
     ```

5. **Verify Persistence:**
   - Close the applet (if visible)
   - Paste again in another app
   - ✅ Clipboard content should still be available

### Success Criteria
- [x] Clipboard works on very first transcription
- [x] No settings toggle required
- [x] Clipboard persists after applet closes
- [x] Log shows "mapped for Wayland"

---

## Test 4: Settings Window Focus (Wayland)

### Expected Behavior
- Settings window should receive keyboard focus when opened
- Should work on both X11 and Wayland
- Should work across virtual desktops

### Test Steps

1. **Test Initial Open:**
   - Click "Settings" from tray menu
   - ✅ Settings window should appear
   - ✅ Window should have keyboard focus (test by typing - search field should receive input)
   - Check logs for:
     ```
     Using QWindow.requestActivate() for Wayland
     ```
     OR
     ```
     Using raise_() + activateWindow() for X11 fallback
     ```

2. **Test Close:**
   - Click "Settings" again (or close button)
   - ✅ Window should close

3. **Test Reopen:**
   - Click "Settings" third time
   - ✅ Window should open with focus
   - Type in search field to verify focus

4. **Test Multi-Desktop (if applicable):**
   - Open settings on desktop 1
   - Switch to desktop 2
   - Click "Settings" from tray
   - ✅ Window should close (you're on desktop 2)
   - Click "Settings" again
   - ✅ Window should open on desktop 2 with focus

### Success Criteria
- [x] Window opens with keyboard focus
- [x] Can type in search field immediately
- [x] Correct activation method used (Wayland vs X11)
- [x] Works across virtual desktops

---

## Test 5: Dismiss Behavior (Popup Mode Switch)

### Expected Behavior
- When applet is in persistent mode, dismissing it should switch to popup mode
- Dismiss can be triggered by double-click or right-click menu
- Next recording should auto-show the applet

### Test Steps

1. **Setup - Enter Persistent Mode:**
   - Right-click tray → "Open Applet"
   - ✅ Applet should be visible and menu shows "Close Applet"

2. **Test Double-Click Dismiss:**
   - Double-click on applet
   - ✅ Applet should hide
   - ✅ Tray menu should now show "Open Applet" (popup mode)
   - Check logs for:
     ```
     Dialog manually dismissed
     Dismiss: switching from persistent to popup mode
     Manually triggering settings coordinator for applet_autohide change
     ```

3. **Test Popup Mode Behavior:**
   - Start recording (Alt+Space)
   - ✅ Applet should auto-show
   - Stop recording
   - ✅ Applet should auto-hide after 500ms

4. **Setup Persistent Again:**
   - Right-click tray → "Open Applet"

5. **Test Right-Click Menu Dismiss:**
   - Right-click on applet → "Dismiss"
   - ✅ Same behavior as double-click
   - ✅ Switches to popup mode
   - Check logs for same messages

6. **Test Dismiss in Popup Mode:**
   - Start recording (applet auto-shows)
   - While recording, double-click applet
   - ✅ Should hide applet
   - ✅ Logs should say "already in popup mode, just hiding"
   - ✅ Should NOT switch modes

### Success Criteria
- [x] Dismiss from persistent mode switches to popup mode
- [x] Double-click dismiss works
- [x] Menu "Dismiss" works
- [x] Dismiss in popup mode just hides (doesn't change mode)
- [x] Next recording auto-shows in popup mode

---

## Test 6: Settings Window Multi-Desktop (Edge Case)

### Expected Behavior
- If settings window is open on another desktop, clicking "Settings" should close it
- Clicking again should open it on current desktop

### Test Steps

1. **Setup - Multiple Desktops:**
   - Ensure you have at least 2 virtual desktops
   - Go to desktop 1

2. **Open Settings on Desktop 1:**
   - Click "Settings" from tray
   - ✅ Settings window opens on desktop 1

3. **Switch to Desktop 2:**
   - Switch to desktop 2 (but leave settings window open on desktop 1)

4. **Close Settings from Desktop 2:**
   - On desktop 2, click "Settings" from tray
   - ✅ Settings window should close (even though it's on desktop 1)

5. **Reopen Settings on Desktop 2:**
   - Click "Settings" again
   - ✅ Settings window should open on desktop 2 with focus

### Success Criteria
- [x] Can close settings window from different desktop
- [x] Reopening opens on current desktop
- [x] Window has focus when reopened

---

## Regression Testing

### Verify Existing Features Still Work

1. **Recording Toggle:**
   - [ ] Alt+Space shortcut starts/stops recording
   - [ ] Tray menu "Start/Stop Recording" works
   - [ ] Left-click on applet toggles recording

2. **Applet Interactions:**
   - [ ] Drag applet to move it
   - [ ] Scroll on applet to resize (100-500px)
   - [ ] Position and size persist after restart

3. **Volume Visualization:**
   - [ ] Radial waveform displays during recording
   - [ ] Colors change with volume (green → yellow → red)
   - [ ] Visualization is smooth

4. **Transcription:**
   - [ ] Transcription completes successfully
   - [ ] Text is copied to clipboard
   - [ ] Notification shows with transcribed text

5. **Settings Persistence:**
   - [ ] Always-on-top setting persists
   - [ ] Applet mode (popup/persistent) persists
   - [ ] Window position/size persists

---

## Known Issues to Verify Still Exist

These issues are **not** fixed by this implementation:

1. **Always-on-top toggle:** Requires restart or toggle off/on to take effect
   - This is a Wayland compositor limitation, not a bug

2. **Window position on Wayland:** May not restore correctly
   - Compositor controls window placement

---

## Logging Tips

### Useful Log Patterns to Watch For

```bash
# Tray menu toggle
grep "Tray menu toggling applet mode" syllablaze-test.log

# Settings coordinator trigger
grep "Manually triggering settings coordinator" syllablaze-test.log

# Klipper attempts
grep -A5 "Attempting to open Klipper" syllablaze-test.log

# Clipboard initialization
grep "ClipboardManager.*Initialized" syllablaze-test.log

# Settings window activation
grep "requestActivate\|raise_()" syllablaze-test.log

# Dismiss behavior
grep "Dialog manually dismissed" syllablaze-test.log
```

---

---

## Test 7: Applet On All Desktops (Bug Fix)

### Expected Behavior
- When in persistent mode, applet should appear on all virtual desktops
- When switching from popup to persistent mode, on-all-desktops should apply automatically

### Test Steps

1. **Setup - Create Multiple Desktops:**
   - Ensure you have at least 2 virtual desktops

2. **Test Initial Startup (Already Working):**
   - Start Syllablaze fresh
   - If default is persistent mode, applet should appear on all desktops
   - Switch between desktops - applet should be visible on all

3. **Test Mode Switch (Bug Fix):**
   - Switch to popup mode (tray → "Close Applet")
   - Switch back to persistent mode (tray → "Open Applet")
   - ✅ Applet should appear
   - ✅ Switch between desktops - applet should be on all desktops
   - Check logs for:
     ```
     Applying on-all-desktops=True in persistent mode
     ```

4. **Test Settings Toggle:**
   - Open Settings → UI
   - Turn autohide OFF (persistent mode)
   - ✅ Applet should appear on all desktops
   - Turn autohide ON (popup mode)
   - Start recording - applet appears
   - ✅ Applet should be on current desktop only (not all)

### Success Criteria
- [x] Applet appears on all desktops at startup (if persistent)
- [x] Applet appears on all desktops when switching to persistent mode
- [x] Applet stays on current desktop in popup mode
- [x] On-all-desktops setting is applied correctly via KWin

---

## Test 8: Settings Window NOT On All Desktops (Bug Fix)

### Expected Behavior
- Settings window should stay on the desktop where it was opened
- Should NOT follow you to other desktops

### Test Steps

1. **Setup - Multiple Desktops:**
   - Ensure you have at least 2 virtual desktops
   - Go to desktop 1

2. **Test Settings Window Desktop Pinning:**
   - Open Settings on desktop 1
   - ✅ Settings window appears
   - Switch to desktop 2
   - ✅ Settings window should NOT be visible on desktop 2
   - Switch back to desktop 1
   - ✅ Settings window should still be there

3. **Test Opening on Different Desktops:**
   - On desktop 1: Open Settings
   - Close Settings
   - Switch to desktop 2
   - Open Settings
   - ✅ Settings window should appear on desktop 2 (not desktop 1)

4. **Check KWin Rule Created:**
   - Check `~/.config/kwinrulesrc` contains:
     ```
     [N]  # some group number
     Description=Syllablaze Settings Window
     title=Syllablaze Settings
     titlematch=1
     onalldesktops=false
     onalldesktopsrule=2
     ```

### Success Criteria
- [x] Settings window stays on desktop where opened
- [x] Does NOT appear on all desktops
- [x] Can be opened on different desktops independently
- [x] KWin rule created with onalldesktops=false

---

## Quick Smoke Test (5 minutes)

If you only have 5 minutes, run this abbreviated test:

1. Fresh start: `pkill syllablaze && python3 -m blaze.main`
2. Record a transcription (Alt+Space, speak, Alt+Space)
3. Paste clipboard - should work ✅
4. Right-click tray → "Open Applet" - should show ✅
5. Right-click tray → "Close Applet" - should hide ✅
6. Double-click applet to dismiss - should switch to popup mode ✅
7. Record again - applet should auto-show ✅
8. Middle-click applet - Klipper should open ✅
9. Click "Settings" - window should open with focus ✅

If all 9 steps pass, the fixes are working correctly.
