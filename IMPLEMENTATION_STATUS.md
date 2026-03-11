# Architectural Review & Exception Handling Overhaul - Implementation Status

## Overview

This document tracks the implementation of the architectural overhaul plan to fix critical backend management issues in Syllablaze.

**Last Updated:** 2026-03-11
**Branch:** `feature/multi-backend-stt`
**Commit:** `9aed67e`

---

## Critical Bugs Being Addressed

### Priority 0: Multiple Active Models + Backend Desync (NEW - 2026-03-11)

**Status:** 🔍 **INVESTIGATION IN PROGRESS** (Phase 0 Complete)

**Symptoms:**
- Multiple models show green "ACTIVE" badge simultaneously in UI
- Wrong backend transcribes despite UI showing correct selection
- User selected Qwen, but Liquid backend was actually processing
- Esperanto transcription garbled (Liquid doesn't support it, thought it was Japanese)

**Impact:** CRITICAL - Users get wrong transcription results

**What Was Done:**
- ✅ Added comprehensive logging throughout model activation flow
- ✅ Added validation to detect multiple active models
- ✅ Added auto-correction when multiple active flags detected
- ✅ Logging in Python (kirigami_integration, transcription_manager, coordinator)
- ✅ Logging in QML (ModelsPage)
- ✅ Created detailed testing instructions (`PHASE_0_TESTING.md`)

**Next Steps:**
1. User runs testing procedure from `PHASE_0_TESTING.md`
2. Analyze logs to identify root cause:
   - Settings write/read timing issue?
   - QML ListView not refreshing?
   - Backend coordinator state desync?
   - Race condition in signal handling?
3. Implement targeted fix based on findings

**Files Modified:**
- `blaze/kirigami_integration.py` - [MODEL_ACTIVATION], [GET_MODELS] logging + validation
- `blaze/main.py` - [BACKEND_REINIT] logging
- `blaze/managers/transcription_manager.py` - [CHECK_BACKEND_CHANGE] logging
- `blaze/managers/coordinator_transcriber.py` - [LOAD_MODEL] logging
- `blaze/backends/coordinator.py` - [COORDINATOR_LOAD] logging
- `blaze/qml/pages/ModelsPage.qml` - Active model validation in QML

---

## Phase 1: Backend Isolation

**Status:** ✅ **COMPLETED** (Previously)

**What Was Fixed:**
- Converted class-level variables to instance variables in `BackendCoordinator`
- Each backend instance now has isolated state
- No more shared mutable state across instances

**Implementation:** Lines 33-38 in `blaze/backends/coordinator.py`

```python
def __init__(self):
    # Instance-level state for proper backend isolation
    self._backends: Dict[str, Type[BaseModelBackend]] = {}
    self._current_backend: Optional[BaseModelBackend] = None
    self._current_model_id: Optional[str] = None
    self._discover_backends()
```

**Result:** Backend isolation working correctly at coordinator level

---

## Phase 2: Transactional Model Loading

**Status:** ⏸️ **PLANNED** (Not Started)

**Goal:** Implement save-try-commit-or-rollback pattern for model switching

**Current Problem:**
- Old model unloaded BEFORE new model validated
- If new model load fails, system has NO model loaded
- User must manually select different model to recover

**Planned Implementation:**

### File: `blaze/backends/coordinator.py`

Add `load_model_atomic()` method that:
1. Validates new model can be loaded
2. Creates new backend instance
3. Loads new model (old still running)
4. On success: unload old, commit new
5. On failure: keep old, discard new

**Benefits:**
- Failed model switches preserve working state
- No application restarts needed
- Graceful degradation

**Complexity:** Medium
**Risk:** Medium - requires careful memory management to avoid OOM

**Blocked By:** Phase 0 testing completion

---

## Phase 3: Exception Handling Improvements

**Status:** ⏸️ **PLANNED** (Not Started)

**Goal:** Add rich context to exceptions for actionable error messages

**Current Problem:**
- Exceptions wrapped 4+ times, losing context
- Users see "Backend failed to initialize" with no guidance
- No information about missing dependencies or memory issues

**Planned Changes:**

### File: `blaze/backends/base.py`

Enhance `ModelLoadError` class:
```python
class ModelLoadError(BackendError):
    def __init__(
        self,
        message: str,
        model_id: str = None,
        backend: str = None,
        device: str = None,
        original_exception: Exception = None
    ):
        # ... store context ...

    def get_user_message(self) -> str:
        """Get user-friendly error message"""
        if isinstance(self.original_exception, ImportError):
            return f"Missing dependencies for {self.backend}. Install required packages."
        elif "CUDA out of memory" in str(self.original_exception):
            return f"Not enough GPU memory for {self.model_id}. Try smaller model or CPU."
        # ... more specific guidance ...
```

**Benefits:**
- Clear, actionable error messages
- Users can self-diagnose issues
- Reduced support burden

**Complexity:** Low
**Risk:** Low

---

## Phase 4: Automatic Fallback Chain

**Status:** ⏸️ **PLANNED** (Not Started)

**Goal:** Keep system operational even after failed model switches

**Current Problem:**
- Failed model load creates "dummy transcriber" and stops
- User must manually select different model
- No attempt to use known-good fallback models

**Planned Implementation:**

### File: `blaze/managers/coordinator_transcriber.py`

```python
FALLBACK_MODELS = ['whisper-tiny', 'whisper-base']

def load_model_with_fallback(self):
    """Load model with automatic fallback to known-good models"""
    target_model = self.settings.get("model")

    for attempt_model in [target_model] + FALLBACK_MODELS:
        try:
            self._load_model(attempt_model)

            if attempt_model != target_model:
                logger.warning(f"Primary model failed, using fallback: {attempt_model}")
                self.transcription_error.emit(
                    f"Could not load {target_model}, using {attempt_model} instead"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to load {attempt_model}: {e}")
            continue

    # All fallbacks exhausted
    logger.error("All model loading attempts failed")
    return False
```

**Benefits:**
- System remains functional
- Automatic recovery from failures
- User notified but not blocked

**Complexity:** Low
**Risk:** Low

---

## Phase 5: Specific Bug Fixes

### Bug 1: Liquid Truncation

**Status:** ⏸️ **INVESTIGATION NEEDED**

**Reported:** User set max_tokens=1024, but still getting truncation

**Possible Causes:**
1. Setting not reaching backend correctly
2. Backend not respecting parameter
3. Memory issues causing early termination
4. Liquid backend bug

**Next Steps:**
1. Add logging to verify setting reaches `backend.transcribe()`
2. Check if memory leaks from state management cause OOM during generation
3. Test with different max_tokens values
4. May be fixed as side effect of memory cleanup improvements

---

### Bug 2: Qwen Multimodal Projector Loading

**Status:** ⏸️ **PLANNED** (Solution Known)

**Error:** `AttributeError: 'Llama' object has no attribute 'load_multimodal_projector'`

**Root Cause:** Using wrong API - multimodal projector must be passed during `Llama()` initialization, not loaded separately

**Fix Required:**

**File:** `blaze/backends/qwen/backend.py:137-146`

**Change from:**
```python
self._llm = Llama(
    model_path=str(self._gguf_path),
    n_ctx=8192,
    n_gpu_layers=n_gpu_layers,
    verbose=False,
)

# Load multimodal projector
self._llm.load_multimodal_projector(str(self._mmproj_path))  # ← WRONG
```

**Change to:**
```python
self._llm = Llama(
    model_path=str(self._gguf_path),
    n_ctx=8192,
    n_gpu_layers=n_gpu_layers,
    chat_format="qwen2-audio",       # ← Enable multimodal
    mmproj=str(self._mmproj_path),   # ← Pass during init
    verbose=False,
)
```

**Complexity:** Low
**Risk:** Low
**Blocked By:** Phase 0 completion (want clean test after model switching is stable)

---

### Bug 3: Qwen Message Format (Type Error)

**Status:** ⏸️ **RESEARCH NEEDED**

**Error:** `TypeError: can only concatenate str (not "list") to str`

**Location:** `blaze/backends/qwen/backend.py:233-247`

**Current Message Format:**
```python
messages=[{
    "role": "user",
    "content": [
        {"type": "audio", "audio_url": tmp_path},
        {"type": "text", "text": prompt}
    ]
}]
```

**Issue:** Need to verify if llama-cpp-python supports this multimodal format

**Next Steps:**
1. Check llama-cpp-python documentation for audio input API
2. May need to use `create_completion()` with embeddings instead
3. Test with official Qwen2-Audio examples

---

### Bug 4: Whisper GPU→CPU Switching

**Status:** ⏸️ **INVESTIGATION NEEDED**

**Reported:** Whisper works on GPU, then switches to CPU after working on other backends

**Hypothesis:**
1. PyTorch CUDA state contamination (likely fixed by backend isolation in Phase 1)
2. Settings not persisting
3. UI not updating settings correctly

**Next Steps:**
1. Test after Phase 0 logging is in place
2. Add device state tracking logs
3. Verify settings persistence
4. May already be fixed by backend isolation improvements

---

## Testing & Verification

### Phase 0 Testing (In Progress)

**Test Document:** `PHASE_0_TESTING.md`

**Key Tests:**
1. Multiple active models detection
2. Backend switching (Whisper → Liquid → Qwen)
3. Language-specific transcription (verify correct backend)
4. Log analysis for state synchronization

**User Action Required:** Run testing procedure and report results

---

### Unit Tests Status

**Existing Tests:** 37 tests passing (from previous work)

**Coverage:**
- `test_backend_architecture.py` (16 tests)
  - Backend derivation from model_id
  - Transcriber type detection
  - Backend health tracking
  - Error messages

- `test_backend_switching.py` (21 tests)
  - Backend selection based on model ID
  - Eager model loading
  - Signal handling

**Tests Needed:**
- Transactional model loading (Phase 2)
- Exception context preservation (Phase 3)
- Fallback chain (Phase 4)
- Multiple active models (Phase 0)

---

## Implementation Priority

### Immediate (This Week)

1. ✅ **Phase 0 Logging** - Complete
2. ⏳ **User Testing** - In Progress
3. ⏳ **Phase 0 Fix** - Waiting for test results

### Short Term (Next Week)

4. ⏸️ **Phase 2: Transactional Loading** - After Phase 0
5. ⏸️ **Phase 5.2: Qwen Projector Fix** - Quick win
6. ⏸️ **Phase 3: Exception Handling** - Improves UX

### Medium Term (This Month)

7. ⏸️ **Phase 4: Fallback Chain** - Robustness
8. ⏸️ **Phase 5.1: Liquid Truncation** - Investigate
9. ⏸️ **Phase 5.3: Qwen Message Format** - Research needed
10. ⏸️ **Phase 5.4: Whisper GPU Switching** - May already be fixed

---

## Files Modified Summary

### Completed (Phase 0 - Commit 9aed67e)

- `blaze/kirigami_integration.py` - +35 lines (logging, validation)
- `blaze/main.py` - +18 lines (logging)
- `blaze/managers/transcription_manager.py` - +12 lines (logging)
- `blaze/managers/coordinator_transcriber.py` - +8 lines (logging)
- `blaze/backends/coordinator.py` - +7 lines (logging)
- `blaze/qml/pages/ModelsPage.qml` - +18 lines (validation, logging)

### To Be Modified (Future Phases)

- `blaze/backends/base.py` - Exception classes (Phase 3)
- `blaze/backends/coordinator.py` - Transactional loading (Phase 2)
- `blaze/managers/coordinator_transcriber.py` - Fallback chain (Phase 4)
- `blaze/backends/qwen/backend.py` - Projector + message format (Phase 5.2, 5.3)

---

## Success Criteria

### Phase 0 Complete When:
- ✅ Logging in place
- ⏳ User testing completed
- ⏳ Root cause identified
- ⏳ Only one model shows as active
- ⏳ Correct backend processes transcriptions

### Overall Project Complete When:
- ⏸️ Backend switches never require restart
- ⏸️ Clear error messages guide users
- ⏸️ System auto-recovers from failures
- ⏸️ All specific bugs fixed
- ⏸️ Comprehensive test coverage
- ⏸️ Memory properly managed during switches

---

## Notes

- Backend isolation (Phase 1) already complete - good foundation
- Phase 0 logging will inform implementation of Phases 2-4
- Some bugs may auto-resolve after architectural fixes
- User testing is critical before proceeding to Phase 2

**Current Focus:** Waiting for Phase 0 test results to determine exact root cause of multiple active models bug.
