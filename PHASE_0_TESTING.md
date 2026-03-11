# Phase 0: Multiple Active Models Bug - Testing Instructions

## Critical Bug Being Investigated

**Symptoms:**
1. Multiple models show green "ACTIVE" badge simultaneously in UI
2. Wrong backend transcribes despite UI showing correct selection
3. Example: User selected Qwen model, but Liquid backend was actually processing audio
4. English works fine (both support it), but Esperanto produces garbled output (Liquid doesn't support it, thought it was Japanese)

**Root Cause Hypothesis:**
- Settings write/read timing issue
- QML ListView not properly refreshing after model change
- Backend coordinator caching wrong backend despite settings change
- Race condition between UI update and backend reload

## What Was Added (Commit 9aed67e)

### Comprehensive Logging Tags

All logging now uses consistent tags for easy filtering:

- `[MODEL_ACTIVATION]` - User activates a model in UI
- `[GET_MODELS]` - Building list of models with active status
- `[BACKEND_REINIT]` - Deferred backend reinitialization
- `[CHECK_BACKEND_CHANGE]` - Checking if backend needs to change
- `[LOAD_MODEL]` - Loading model through coordinator transcriber
- `[COORDINATOR_LOAD]` - Backend coordinator loading model

### Validation & Auto-Correction

**Python (kirigami_integration.py:420-438):**
```python
# Validate: Only ONE model should be active
active_count = sum(1 for m in models if m.get("active", False))
if active_count > 1:
    active_models = [m["id"] for m in models if m.get("active", False)]
    logger.error(
        f"[GET_MODELS] CRITICAL: Multiple models marked as active! "
        f"Active models: {active_models}, current_model setting: {current_model}"
    )
    # Auto-correct: Force clear all active flags and re-set correctly
    for m in models:
        m["active"] = (m["id"] == current_model)
    logger.warning("[GET_MODELS] Forced correction of active flags")
```

**QML (ModelsPage.qml:265-279):**
```qml
// Validate: Check for multiple active models
var activeModels = []
for (var j = 0; j < modelArray.length; j++) {
    if (modelArray[j].active) {
        activeModels.push(modelArray[j].id)
    }
}
console.log("[ModelsPage] Active models:", JSON.stringify(activeModels))

if (activeModels.length > 1) {
    console.error("[ModelsPage] CRITICAL: Multiple active models detected:", activeModels)
}
```

## How to Test

### Prerequisites

1. Ensure you have multiple backends available:
   - Whisper (should always be available)
   - Liquid (requires `liquid-audio` package)
   - Qwen (requires `llama-cpp-python` with audio support)

2. Have models downloaded for at least 2 different backends

### Testing Procedure

#### Step 1: Start with Clean Logging

```bash
# Restart the app with logging visible
systemctl --user restart syllablaze.service
journalctl --user -u syllablaze.service -f | grep -E '\[MODEL_ACTIVATION\]|\[GET_MODELS\]|\[BACKEND_REINIT\]|\[CHECK_BACKEND_CHANGE\]|\[LOAD_MODEL\]|\[COORDINATOR_LOAD\]'
```

#### Step 2: Note Initial State

1. Open Syllablaze Settings → Models tab
2. Note which model currently has the green "ACTIVE" badge
3. Check logs for initial state:
   - `[GET_MODELS] Current active model from settings: <model-name>`
   - `[GET_MODELS] Marking model as ACTIVE: <model-name>`
   - Should see ONLY ONE model marked as active

#### Step 3: Switch to Different Backend

1. In Models tab, filter by a DIFFERENT backend (e.g., if Liquid is active, switch to Qwen)
2. Click "Activate" on a model from the different backend
3. Watch the logs in real-time:

**Expected log sequence:**
```
[MODEL_ACTIVATION] START: Setting active model to <new-model>
[MODEL_ACTIVATION] Previous active model: <old-model>
[MODEL_ACTIVATION] Settings updated. Verification: <new-model>
[MODEL_ACTIVATION] Model <new-model> uses backend '<backend-name>'
[MODEL_ACTIVATION] Emitting activeModelChanged signal
[MODEL_ACTIVATION] COMPLETE

[GET_MODELS] Current active model from settings: <new-model>
[GET_MODELS] Marking model as ACTIVE: <new-model>

[BACKEND_REINIT] Deferred reinitialization starting for model: <new-model>
[BACKEND_REINIT] Current transcriber type: <old-type>

[CHECK_BACKEND_CHANGE] Current model from settings: <new-model>
[CHECK_BACKEND_CHANGE] Expected backend for <new-model>: <backend-name>
[CHECK_BACKEND_CHANGE] Current transcriber type: <old-type>
[CHECK_BACKEND_CHANGE] Expected transcriber type: <new-type>

[LOAD_MODEL] Loading model via coordinator: <new-model>
[LOAD_MODEL] Previous model: <old-model>
[LOAD_MODEL] CoordinatorTranscriber: Loading model <new-model> with device=<device>

[COORDINATOR_LOAD] Loading model: <new-model> on <device> (backend: <backend>, switch: true, old_backend: <old>, old_model: <old-model>)
[COORDINATOR_LOAD] Calling backend.load() for <backend-name>
[COORDINATOR_LOAD] ✓ Model loaded successfully: <new-model> (backend: <backend-name>, device: <device>)

[LOAD_MODEL] Successfully loaded <new-model>, updated _current_model_name

[BACKEND_REINIT] After reinitialization: transcriber type=<new-type>, success=True
[BACKEND_REINIT] Successfully reinitialized for model: <new-model>
```

4. Check the UI:
   - **CRITICAL:** Only the newly activated model should have green "ACTIVE" badge
   - Old model's badge should disappear
   - If you see multiple active badges → **BUG REPRODUCED**

5. Check QML console logs (in terminal or Settings → Debug):
   - `[ModelsPage] Active models: ["<new-model>"]` (should be array with ONE model)
   - If multiple models in array → **BUG REPRODUCED**

#### Step 4: Verify Correct Backend is Transcribing

**Test with language-specific transcription:**

1. For **Qwen** (supports 10,000+ languages):
   - Record audio in Esperanto, Chinese, Arabic, or another non-English language
   - Transcription should be accurate
   - If garbled or treated as wrong language → **WRONG BACKEND**

2. For **Liquid** (English-focused):
   - Record audio in English
   - Should work well
   - If you try non-English, it may treat it as Japanese

3. For **Whisper** (multilingual):
   - Record in any supported language
   - Should work correctly

**Check logs during transcription:**
```bash
journalctl --user -u syllablaze.service -f | grep -i 'transcrib'
```

Look for confirmation of which backend is processing the audio.

#### Step 5: Switch Multiple Times

1. Switch back and forth between backends several times:
   - Whisper → Liquid → Qwen → Whisper → Qwen
2. After EACH switch:
   - Check only ONE active badge visible
   - Check logs show correct backend loading
   - Perform a quick transcription test

### What to Look For

#### 🟢 GOOD Signs (Bug NOT Present)

- Only ONE model shows active badge at any time
- `[GET_MODELS] Marking model as ACTIVE:` appears ONCE per refresh
- No `CRITICAL: Multiple models marked as active` errors
- QML logs show single-element array: `["model-name"]`
- Settings verification matches: `Verification: <expected-model>`
- Correct backend loads: `COORDINATOR_LOAD] ✓ Model loaded successfully`
- Transcription uses correct backend (language support matches)

#### 🔴 BAD Signs (Bug IS Present)

- Multiple green "ACTIVE" badges visible simultaneously
- `[GET_MODELS] Marking model as ACTIVE:` appears MULTIPLE times
- Error: `CRITICAL: Multiple models marked as active!`
- QML logs show multi-element array: `["model-1", "model-2"]`
- Settings verification fails: `SETTINGS WRITE FAILED!`
- Wrong backend loads (doesn't match UI selection)
- Transcription fails for languages only supported by selected model
- Auto-correction triggered: `Forced correction of active flags`

### Expected Outcomes

#### If Bug is NOT Reproduced

Great! The logging will help prevent future issues and makes debugging easier.

#### If Bug IS Reproduced

The logs will show exactly WHERE the problem occurs:

1. **Settings Write Failure:**
   - `[MODEL_ACTIVATION] SETTINGS WRITE FAILED!`
   - → Settings layer issue

2. **Multiple Active in Python:**
   - `[GET_MODELS] CRITICAL: Multiple models marked as active!`
   - → Logic error in active status determination

3. **Wrong Backend Loaded:**
   - `[COORDINATOR_LOAD]` shows different backend than expected
   - → Backend coordinator caching/state issue

4. **QML List Not Refreshing:**
   - Python logs show correct single active model
   - QML shows multiple active models
   - → QML ListView not updating properly

## Reporting Results

Please provide:

1. **Full log output** from the testing session (use the grep filter above)
2. **Screenshots** of the Models page showing active badges
3. **Transcription results** (especially for language-specific tests)
4. **Which scenario** reproduced the bug (if any)
5. **System info:**
   - Python version: `python --version`
   - Qt version: `python -c "from PyQt6.QtCore import qVersion; print(qVersion())"`
   - Backends available: Check Settings → Dependencies

## Next Steps After Testing

### If Bug Reproduced

Based on log analysis, implement targeted fixes:

- **Phase 1:** Fix settings synchronization if needed
- **Phase 2:** Fix QML ListView refresh if needed
- **Phase 3:** Fix backend coordinator state if needed
- **Phase 4:** Implement transactional model loading (from plan)

### If Bug NOT Reproduced

- Keep logging in place for production monitoring
- Move to other phases of the plan:
  - Phase 2: Transactional Model Loading
  - Phase 3: Exception Handling Improvements
  - Phase 5: Fix Qwen Multimodal Projector
  - Phase 6: Investigate Liquid Truncation

## Contact

If you encounter issues or need clarification, reference:
- This document: `PHASE_0_TESTING.md`
- Implementation plan: See user's original request
- Commit: `9aed67e` - "feat: Add comprehensive logging to diagnose multiple active models bug"
