# Changelog

All notable changes to Syllablaze will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.8] - 2026-02-19

### 🎉 Highlights

Version 0.8 represents a major milestone for Syllablaze with comprehensive documentation, architectural improvements, and enhanced stability. This release focuses on making the project more maintainable, better documented, and more reliable for users.

### 📚 Documentation Overhaul

- **Professional Documentation Site**: New MkDocs-based documentation with Material theme
- **Divio Documentation System**: Organized into Tutorials, How-To Guides, Reference, and Explanation
- **User Guides**: Complete installation, quick start, troubleshooting, and settings reference
- **Developer Guides**: Setup instructions, architecture overview, testing guide, and contribution guidelines
- **Architecture Decision Records (ADRs)**: Documented key design decisions (Manager Pattern, QML Kirigami UI, Settings Coordinator)
- **Enhanced CLAUDE.md**: Added file map, critical constraints, and common agent tasks for AI-assisted development

### 🏗️ Architecture Improvements

- **Orchestration Layer**: Implemented `SyllablazeOrchestrator` for clean separation between UI and backend
- **Manager Pattern**: Refactored components into focused managers (AudioManager, UIManager, SettingsCoordinator, etc.)
- **Settings Coordinator**: New derivation pattern for managing high-level and backend settings
- **Window Visibility Coordinator**: Centralized control of recording dialog visibility
- **Application State**: Single source of truth for application state management

### 🎨 UI Enhancements

- **Applet Mode Improvements**: Enhanced circular recording dialog with better volume visualization
- **Settings Window**: Kirigami-based settings with organized pages (Models, Audio, Transcription, Shortcuts, UI, About)
- **Progress Windows**: Better visual feedback during recording and transcription
- **Tray Menu**: Improved system tray integration with state-aware menu items

### 🐛 Bug Fixes & Stability

- **Clipboard on Wayland**: Fixed clipboard persistence issues when recording dialog auto-hides
- **Window Management**: Resolved always-on-top and window positioning issues on Wayland
- **Global Shortcuts**: Improved reliability of keyboard shortcuts on both X11 and Wayland
- **Error Handling**: Better error messages and recovery from failed operations
- **Recording Stability**: Prevents recording during transcription to avoid conflicts

### 🔧 Developer Experience

- **Testing Framework**: Comprehensive test suite with mocks for PyAudio and hardware
- **CI/CD**: GitHub Actions workflow with flake8 linting, pytest, and documentation build
- **Code Quality**: Established flake8 standards (max-line-length=127, max-complexity=10)
- **Development Scripts**: `dev-update.sh` for rapid development iteration

### 📦 Project Structure

- **Clean Root Directory**: Reduced from 10+ markdown files to 3 (README, CLAUDE, CONTRIBUTING)
- **Archive System**: Organized temporary documentation with retention policy
- **Documentation Organization**: 33 active docs in structured directories
- **GitHub Migration**: Updated all references to new Zebastjan/Syllablaze repository

### Known Issues

- Window position persistence on Wayland (compositor limitation)
- Always-on-top toggle may require restart on Wayland

---

## [0.5] - 2026-02-15

### ✨ New Features

- **Global Keyboard Shortcuts**: True system-wide hotkeys using `pynput`
- **KDE Wayland Support**: Shortcuts work even when switching windows
- **Single Toggle Shortcut**: Simplified UX with Alt+Space default
- **Kirigami Settings UI**: Native KDE Plasma styling
- **Recording Dialog**: Optional circular volume indicator

### 🐛 Bug Fixes

- Improved stability preventing recording during transcription
- Better window management with progress window always on top

---

## [0.4 beta] - 2026-02-10

### ⚡ Performance

- Migrated to Faster Whisper for improved transcription speed

---

## [0.3] - 2026-02-05

### 🔒 Privacy & Performance

- **Enhanced Privacy**: Audio processed entirely in memory (no temp files)
- **Direct 16kHz Recording**: Optimized for Whisper, reduces processing time
- **Improved Recording UI**: Better window with app info and settings display

---

## Roadmap

### Coming in v1.0

The following features are planned for the v1.0 release:

#### 🎯 SyllabBlurb — Transcription Staging Widget

A floating staging widget that intercepts transcribed text before it reaches its destination:

- **Two-Lane Architecture**: Separate paths for system clipboard and direct insert
- **Editable Preview**: Review and edit transcription before sending
- **Direct Insert Mode**: Bypass clipboard entirely by dragging text to target
- **Post-Processing Toolbar**: LLM integration for filler removal, conciseness, translation
- **Privacy-First**: Option to never touch system clipboard

See full design: [SyllabBlurb Design Doc](SyllabBlurb%20Transcription%20Staging%20%20Post-Processing%20Widget.md)

#### 🎨 Enhanced Applet Visualization

Programmatic dot patterns for the recording dialog waveform visualization:

- **Multiple Pattern Styles**: Dots radar, dots curtains, dots radial, and more
- **Code-Generated Visuals**: No SVG editing required for new patterns
- **Dynamic Window Sizing**: Tight when idle, expanded when recording
- **Real-time Audio Visualization**: Responsive to volume with color gradients

See full design: [Applet Visualization Design Doc](Syllablaze%20Applet%20Visualization%20Programmatic%20Dot%20Patterns.md)

#### 📋 Clipboard-Free Operation

Full support for using Syllablaze without touching the system clipboard:

- **Direct Insert**: Drag transcribed text directly to target applications
- **Clipboard Bypass Mode**: Configuration option to disable clipboard entirely
- **Better Privacy**: Text never passes through shared clipboard
- **Integration with SyllabBlurb**: Seamless workflow with staging widget

### Future Ideas

- **Transcription History**: Persistent log of past transcriptions
- **Flatpak Packaging**: Distribution through Flatpak for broader Linux support
- **Model Benchmarking**: Built-in performance testing for different Whisper models
- **D-Bus Interface**: External control API for automation

---

## Version History Summary

| Version | Date | Focus |
|---------|------|-------|
| 0.8 | 2026-02-19 | Documentation, architecture, stability |
| 0.5 | 2026-02-15 | Global shortcuts, Wayland support, Kirigami UI |
| 0.4 beta | 2026-02-10 | Faster Whisper integration |
| 0.3 | 2026-02-05 | Privacy improvements, in-memory processing |

---

*For detailed migration guides and breaking changes, see the [Project Milestones](Syllablaze%20Project%20Milestones.md) document.*
