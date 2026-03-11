# Testing Qwen Automated Installation

## Overview

This document describes how to test the new automated llama-mtmd-cli installation feature for the Qwen backend.

## What Was Implemented

### 1. Shell Script (`blaze/scripts/install_llama_mtmd_cli.sh`)
- Automated build script that handles entire compilation process
- Auto-detects CUDA availability (builds GPU version if available, CPU-only otherwise)
- Installs to `~/.local/bin` (no sudo required)
- Reports progress via parseable output: `PROGRESS:percent:message`
- Handles errors with clear messages: `ERROR:message`
- Cleanup guaranteed via trap (removes temp build directory)

### 2. Python Integration (`blaze/backends/dependency_manager.py`)
- `install_qwen_binary()`: Runs shell script with progress reporting
- `uninstall_qwen_binary()`: Removes binary from `~/.local/bin`
- `install_qwen_backend()`: Updated to support auto-install (new parameter: `auto_install_binary`)
- `uninstall_qwen_backend()`: Updated to also remove binary

### 3. Qt/QML UI Integration
- **Settings Bridge** (`blaze/backends/settings_bridge.py`):
  - New method: `installQwenBinary()` - Triggers automated installation
  - Uses existing progress signals (`dependencyInstallProgress`, `dependencyInstallComplete`)

- **Dependencies Page** (`blaze/qml/pages/DependenciesPage.qml`):
  - When Qwen has Python deps but no binary: shows "Auto Install Binary" button
  - Separate "Manual Instructions" button for advanced users
  - Progress bar shows compilation status with granular messages
  - Instructions dialog updated to clarify it's for advanced/manual setup

## Test Scenarios

### Prerequisites
Before testing, ensure you have build dependencies:
```bash
sudo pacman -S git cmake base-devel
# Optional for GPU support:
sudo pacman -S cuda
```

### Test 1: Clean Install (No Dependencies)
**Setup:**
```bash
# Start with clean slate - no Qwen installed
pip uninstall -y huggingface-hub
rm -f ~/.local/bin/llama-mtmd-cli
```

**Steps:**
1. Open Syllablaze → Settings → Dependencies
2. Find "Qwen2.5-Omni" backend
3. Click "Install" button
4. Should install Python dependencies only
5. Page refreshes, now shows "Auto Install Binary" button

**Expected:**
- First install: Python packages only (quick)
- Button changes to "Auto Install Binary"
- Status shows "Setup Incomplete"

---

### Test 2: Automated Binary Installation
**Setup:**
```bash
# Have Python deps but no binary
pip install huggingface-hub
rm -f ~/.local/bin/llama-mtmd-cli
```

**Steps:**
1. Open Syllablaze → Settings → Dependencies
2. Find "Qwen2.5-Omni" backend
3. Click "Auto Install Binary" button
4. Watch progress bar (5-15 minutes)
5. Observe progress messages:
   - "Checking build dependencies..."
   - "Cloning llama.cpp repository..."
   - "Configuring build with CMake..."
   - "Compiling: X/Y files" (many updates)
   - "Installing to ~/.local/bin..."
   - "Verifying installation..."
   - "Installation complete!"

**Expected:**
- Progress bar shows 0% → 100%
- Messages update frequently during compilation
- After completion: Status shows "✓ Installed"
- Binary exists: `ls -lh ~/.local/bin/llama-mtmd-cli`
- Binary works: `llama-mtmd-cli --help`

**Timing:**
- CPU-only build: ~10-15 minutes
- CUDA-enabled build: ~8-12 minutes (varies by GPU)

---

### Test 3: CUDA Detection
**Setup:**
```bash
# Test on system with CUDA installed
which nvcc  # Should show path to nvcc
```

**Steps:**
1. Run automated installation (Test 2)
2. Check early progress messages for CUDA detection

**Expected:**
- If CUDA available: "CUDA detected: version X.Y"
- If no CUDA: "CUDA not found, building CPU-only version"
- Binary should be built with appropriate support

**Verify CUDA build:**
```bash
ldd ~/.local/bin/llama-mtmd-cli | grep cuda
# Should show libcudart.so if CUDA build succeeded
```

---

### Test 4: Error Handling (Missing Dependencies)
**Setup:**
```bash
# Temporarily hide cmake to trigger error
sudo mv /usr/bin/cmake /usr/bin/cmake.bak
```

**Steps:**
1. Click "Auto Install Binary"
2. Observe error message

**Expected:**
- Progress stops at ~2%
- Error shown: "CMake not installed. Install with: sudo pacman -S cmake"
- Installation fails gracefully
- No partial artifacts left behind

**Cleanup:**
```bash
sudo mv /usr/bin/cmake.bak /usr/bin/cmake
```

---

### Test 5: Manual Instructions (Fallback)
**Steps:**
1. Have Qwen in partial state (Python deps, no binary)
2. Click "Manual Instructions" button
3. Review instructions dialog

**Expected:**
- Dialog title: "Qwen Setup Instructions (Manual/Advanced)"
- Subtitle mentions: "Use 'Auto Install Binary' for automated setup"
- Shows traditional copy-paste commands
- "Copy Install Commands" button available

---

### Test 6: Uninstallation
**Setup:**
```bash
# Have fully installed Qwen
pip install huggingface-hub
# ... run automated binary install ...
```

**Steps:**
1. Open Dependencies tab
2. Find Qwen backend (shows "✓ Installed")
3. Click "Uninstall" button
4. Confirm uninstallation

**Expected:**
- Removes Python packages: `huggingface-hub`
- Removes binary: `~/.local/bin/llama-mtmd-cli`
- Status changes to unavailable
- Shows "Install" button again

**Verify:**
```bash
pip show huggingface-hub  # Should error (not installed)
ls ~/.local/bin/llama-mtmd-cli  # Should error (not found)
```

---

### Test 7: Reinstallation
**Steps:**
1. After Test 6 (uninstallation), click "Install" again
2. Then click "Auto Install Binary"
3. Verify works from clean state

**Expected:**
- Should rebuild from scratch
- Progress identical to Test 2
- Installation succeeds

---

### Test 8: Already Installed (Skip Build)
**Setup:**
```bash
# Binary already in PATH
ls -lh ~/.local/bin/llama-mtmd-cli  # Exists
```

**Steps:**
1. Click "Install" on Qwen
2. Observe behavior

**Expected:**
- Skips binary build entirely
- Quickly reports: "llama-mtmd-cli found, Qwen ready!"
- Immediately shows "✓ Installed"

---

### Test 9: Integration with Backend
**Prerequisites:**
- Fully installed Qwen (Test 2 completed)
- Downloaded Qwen model (e.g., qwen2.5-omni-3b-q8)

**Steps:**
1. Open Settings → Models → Qwen tab
2. Activate qwen2.5-omni-3b-q8 model
3. Record audio clip (10-15 seconds)
4. Transcribe

**Expected:**
- No "missing libmtmd.so.0" error
- Transcription completes successfully
- Qwen backend uses installed binary

---

### Test 10: Cancel Installation (Future Enhancement)
**Note:** Current implementation doesn't support cancel, but UI shows cancel button.

**Steps:**
1. Start auto-install
2. Click cancel button during compilation

**Expected (current):**
- Cancel button visible but may not work
- Installation continues in background

**TODO:** Add process.terminate() support in Python

---

## Success Criteria

- ✅ Clean install works (no manual steps required)
- ✅ CUDA auto-detection works correctly
- ✅ Progress reporting is clear and frequent
- ✅ Error messages are actionable
- ✅ Uninstall removes both Python packages and binary
- ✅ Reinstall works after uninstall
- ✅ Binary verification catches missing libraries
- ✅ Installation to ~/.local/bin works (no sudo)
- ✅ Backend uses installed binary successfully

## Known Limitations

1. **Compilation Time:** 5-15 minutes is long (consider pre-built binaries in future)
2. **Cancel Not Implemented:** Cancel button shown but doesn't terminate build
3. **Build Logs:** Not exposed in UI (user can't see detailed compiler output)
4. **Disk Space:** Requires ~2GB temp space during build (cleaned up after)
5. **Dependencies:** User must manually install git/cmake/gcc if missing

## Future Enhancements

1. **Pre-built Binaries:** Distribute compiled binaries for common platforms
2. **Build Caching:** Keep compiled binary cached for faster reinstalls
3. **Cancel Support:** Add subprocess.terminate() when user cancels
4. **Build Log Viewer:** Show full compilation output in expandable log
5. **Progress Estimation:** More accurate time remaining estimates
6. **Parallel Downloads:** Download model while binary compiles

## Troubleshooting

### Build Fails with "missing library"
```bash
# Check build dependencies
pacman -Q git cmake base-devel

# For CUDA builds:
pacman -Q cuda
nvcc --version
```

### Binary verification fails
```bash
# Check shared library dependencies
ldd ~/.local/bin/llama-mtmd-cli

# Look for "not found" entries
# Install missing libraries via pacman
```

### "Already running" error
```bash
# Kill any stuck build processes
pkill -f "install_llama_mtmd_cli.sh"

# Remove temp directories
rm -rf /tmp/llama-cpp-build.*
```

### Binary not found after install
```bash
# Check if ~/.local/bin is in PATH
echo $PATH | grep "$HOME/.local/bin"

# If not, add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"
```

## Log Files

Installation logs are written to:
- **Python logs:** Check Syllablaze output console
- **Shell script:** Stdout/stderr captured by Python subprocess
- **Build output:** Temporary files cleaned up after completion

To preserve logs for debugging:
```bash
# Run script manually with logging
bash -x blaze/scripts/install_llama_mtmd_cli.sh 2>&1 | tee install.log
```
