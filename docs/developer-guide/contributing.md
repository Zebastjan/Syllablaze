# Contributing to Syllablaze

Thank you for your interest in contributing! This page is a quick reference - see [CONTRIBUTING.md](../../CONTRIBUTING.md) in the repository root for the complete guide.

## Quick Start

1. **Fork and clone:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Syllablaze.git
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Run tests:**
   ```bash
   pytest
   ```

4. **Make changes and test:**
   ```bash
   python3 -m blaze.main  # Run from source
   ```

5. **Submit PR:**
   - Push to your fork
   - Open PR on GitHub
   - Pass CI checks

## Essential Guidelines

### Code Style
- **Linting:** flake8 with `max-line-length=127`
- **Complexity:** max 10 (flake8 complexity check)
- **Docstrings:** Google style for functions/classes
- **Type hints:** Optional but encouraged

### Testing
- **Required:** Unit tests for new features
- **Coverage:** Aim for >80% on new code
- **Mocks:** Use `MockPyAudio`, `MockSettings` from conftest.py
- **Markers:** Add `@pytest.mark.audio` / `@pytest.mark.ui` etc.

### Documentation
- **User-facing:** Update `docs/user-guide/`
- **Developer:** Update `docs/developer-guide/`
- **ADRs:** Create ADR for architectural decisions
- **CLAUDE.md:** Update file map for new modules

### Git Workflow
- **Branch:** `feature/description` or `fix/description`
- **Commits:** Conventional commits format: `feat:`, `fix:`, `docs:`, etc.
- **PR:** Fill template, pass CI, address review feedback

## Where to Contribute

### Good First Issues

Check [GitHub Issues](https://github.com/Zebastjan/Syllablaze/issues) labeled `good-first-issue`.

### Documentation

- Add examples to user guide
- Improve troubleshooting with common issues
- Translate documentation
- Fix typos or broken links

### Features

See [Roadmap](../roadmap/) for planned features.

### Bug Fixes

Check [Known Issues Bug Tracker](../roadmap/Syllablaze%20Known%20Issues%20Bug%20Tracker.md).

## Getting Help

- **Documentation:** Start with this site
- **GitHub Discussions:** Ask questions
- **CLAUDE.md:** Architecture reference for developers
- **Issues:** Report bugs or request features

---

**Full details:** [CONTRIBUTING.md](../../CONTRIBUTING.md)
