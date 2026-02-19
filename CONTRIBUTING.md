# Contributing to Syllablaze

Thank you for your interest in contributing to Syllablaze! This document provides guidelines for contributing to the project.

## 🌟 Project Vision

Syllablaze aims to provide a seamless, privacy-focused speech-to-text experience for KDE Plasma users on Linux. We prioritize:

- **Privacy:** All audio processing happens in-memory (no temp files)
- **Native Integration:** Tight KDE Plasma integration with Kirigami UI
- **User Experience:** Simple, intuitive interface with sensible defaults
- **Performance:** Efficient resource usage with optional GPU acceleration
- **Agent-Friendly Development:** AI-assisted development with comprehensive documentation

## 📋 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Welcome newcomers and help them learn
- Report unacceptable behavior to project maintainers

## 🚀 Getting Started

### Fork and Clone

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/syllablaze.git
cd syllablaze
```

### Development Setup

See [Developer Guide: Setup](docs/developer-guide/setup.md) for detailed instructions:

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly during development
python3 -m blaze.main

# Run tests
pytest
```

### Quick Development Update

Use the `dev-update.sh` script to copy changes to your pipx installation and restart:

```bash
./blaze/dev-update.sh
```

## 💻 Development Workflow

### Branch Naming

- **Feature:** `feature/short-description` (e.g., `feature/gpu-detection`)
- **Bug fix:** `fix/issue-description` (e.g., `fix/wayland-clipboard`)
- **Documentation:** `docs/topic` (e.g., `docs/troubleshooting`)
- **Refactoring:** `refactor/component` (e.g., `refactor/settings-coordinator`)

### Commit Messages

Follow the conventional commits style:

```
<type>: <short summary>

<optional detailed description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring (no behavior change)
- `test:` - Adding or updating tests
- `chore:` - Build process, dependencies, tooling

**Examples:**
```
feat: add GPU detection for CUDA acceleration

Implements automatic CUDA library detection with LD_LIBRARY_PATH
configuration and process restart for GPU acceleration.
```

```
fix: resolve clipboard copy on Wayland

Use persistent clipboard service to prevent data loss when
recording dialog is hidden on Wayland compositors.
```

## 🔍 Pull Request Process

### Before Submitting

1. **Run tests:** `pytest` - All tests must pass
2. **Run linter:** `flake8 . --max-line-length=127` - No linting errors
3. **Update documentation:** See documentation checklist below
4. **Test on both X11 and Wayland** (if window management changes)

### PR Checklist

When opening a pull request, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Code follows flake8 style (max-line-length=127, max-complexity=10)
- [ ] Docstrings added/updated for new functions/classes (Google style)
- [ ] CLAUDE.md updated if new pattern or module added
- [ ] User-facing documentation updated (troubleshooting, settings reference)
- [ ] Architecture Decision Record (ADR) created if significant design decision
- [ ] Testing scenarios added to `docs/developer-guide/testing.md` if applicable
- [ ] Commit messages follow conventional commits format

### Documentation Checklist

**On every feature addition:**
- [ ] Add docstrings to new classes/methods (Google style)
- [ ] Update CLAUDE.md file map if new module
- [ ] Update `docs/user-guide/settings-reference.md` if new setting
- [ ] Create ADR if significant design decision
- [ ] Update relevant user guide page

**On every bug fix:**
- [ ] Update `docs/getting-started/troubleshooting.md` if user-facing
- [ ] Update `docs/roadmap/Syllablaze Known Issues Bug Tracker.md`
- [ ] Update `docs/explanation/wayland-support.md` if Wayland-specific

**Before PR merge:**
- [ ] Verify doc build passes: `mkdocs build --strict`
- [ ] Check no broken links in changed pages
- [ ] Update `docs/developer-guide/testing.md` if test scenarios change

### Review Process

1. Maintainers will review your PR within 7 days
2. Address feedback by pushing new commits (don't force-push during review)
3. Once approved, maintainers will merge using "Squash and merge"
4. Your contribution will be acknowledged in release notes

## 🤖 Agent-Driven Development

Syllablaze embraces AI-assisted development with Claude Code. When working with AI agents:

### Updating CLAUDE.md

When adding new components or patterns:

1. Update the **File Map** section with the new module location
2. Add to **Critical Constraints** if there are NEVER/ALWAYS patterns
3. Update **Common Agent Tasks** if you've established a new workflow

### Creating Architecture Decision Records (ADRs)

For significant architectural decisions:

1. Copy `docs/adr/template.md` to `docs/adr/XXXX-title.md`
2. Number sequentially (0001, 0002, ...)
3. Fill all sections: Context, Decision, Consequences, Alternatives
4. Reference from code comments where decision is implemented
5. Link from related explanation docs
6. Add to `mkdocs.yml` nav under ADRs section

**When to create an ADR:**
- New manager or coordinator introduced
- Significant refactoring changing multiple components
- Choosing between alternative approaches (e.g., Qt vs D-Bus)
- Establishing new patterns or conventions
- Wayland-specific workarounds with architectural impact

### Best Practices for Agent Collaboration

- Provide clear, specific prompts to agents
- Reference CLAUDE.md file map when asking for changes
- Review agent-generated code for Qt/Wayland best practices
- Test agent changes on both X11 and Wayland
- Update documentation immediately after agent-driven changes

## 🧪 Testing Guidelines

See [Testing Guide](docs/developer-guide/testing.md) for comprehensive testing documentation.

### Test Organization

- `tests/conftest.py` - Shared fixtures and mocks
- `tests/test_*.py` - Unit tests organized by module
- Use pytest markers: `@pytest.mark.audio`, `@pytest.mark.ui`, etc.

### Running Tests

```bash
# Run all tests
pytest

# Run specific category
pytest -m audio
pytest -m ui

# Run specific test file
pytest tests/test_audio_processor.py

# Run with coverage
pytest --cov=blaze --cov-report=html
```

### Writing Tests

- Follow existing test patterns in `tests/conftest.py`
- Use mocks (`MockPyAudio`, `MockSettings`) to avoid hardware dependencies
- Test both success and failure cases
- Add docstrings explaining what each test verifies

## 🎨 Code Style

### Linting

CI enforces **flake8** with these settings:
- `max-line-length=127`
- `max-complexity=10`

Optionally, you can use **ruff** during development:
```bash
ruff check blaze/ --fix
```

**Note:** No formatter (black/autopep8) is configured. Follow existing code style.

### Python Style Guidelines

- Use Google-style docstrings
- Follow PEP 8 naming conventions
- Prefer explicit over implicit
- Use type hints where they improve clarity
- Keep functions focused (single responsibility)

### Qt/PyQt6 Best Practices

See [Patterns & Pitfalls](docs/developer-guide/patterns-and-pitfalls.md) for detailed guidance:

- Use signals/slots for inter-component communication
- Never call `show()/hide()` directly on recording dialog - use `ApplicationState.set_recording_dialog_visible()`
- Connect to `QWindow::visibilityChanged` instead of `QTimer.singleShot()` for window mapping
- Test on both X11 and Wayland
- Update KWin rules when changing window properties

## 🐛 Reporting Bugs

Use [GitHub Issues](https://github.com/Zebastjan/Syllablaze/issues) to report bugs.

### Bug Report Template

```markdown
**Environment:**
- Syllablaze version: (from Settings → About)
- KDE Plasma version: (from `plasmashell --version`)
- Session type: X11 or Wayland (check `echo $XDG_SESSION_TYPE`)
- Linux distribution and version:

**Steps to Reproduce:**
1. Open Syllablaze
2. Click...
3. See error

**Expected Behavior:**
What you expected to happen

**Actual Behavior:**
What actually happened

**Logs:**
Enable debug logging in Settings → About, reproduce the issue, and attach relevant log excerpt from `~/.local/state/syllablaze/syllablaze.log`
```

## 📚 Where to Get Help

- **Documentation:** Start with [docs/index.md](docs/index.md)
- **GitHub Discussions:** Ask questions and share ideas
- **Known Issues:** Check [docs/roadmap/Syllablaze Known Issues Bug Tracker.md](docs/roadmap/Syllablaze%20Known%20Issues%20Bug%20Tracker.md)
- **Troubleshooting:** See [docs/getting-started/troubleshooting.md](docs/getting-started/troubleshooting.md)

## 📝 License

By contributing to Syllablaze, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Syllablaze! 🎉
