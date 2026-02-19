# Development Setup

Set up your development environment for contributing to Syllablaze.

## Prerequisites

- Python 3.8+
- Git
- portaudio development headers
- pipx (optional, for testing installed version)

## Step 1: Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/Syllablaze.git
cd Syllablaze
```

3. Add upstream remote:

```bash
git remote add upstream https://github.com/PabloVitasso/Syllablaze.git
```

## Step 2: Install Dependencies

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt install python3-dev portaudio19-dev

# Fedora
sudo dnf install python3-devel portaudio-devel

# Arch
sudo pacman -S python portaudio
```

### Python Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

## Step 3: Run Syllablaze Directly

```bash
python3 -m blaze.main
```

This runs Syllablaze directly from source without installing via pipx.

## Step 4: Development Workflow

### Make Changes

1. Create feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes

3. Run tests:
   ```bash
   pytest
   ```

4. Run linter:
   ```bash
   flake8 . --max-line-length=127
   ```

### Test Installed Version

Use the `dev-update.sh` script to test changes in pipx environment:

```bash
./blaze/dev-update.sh
```

This script:
1. Copies changed files to pipx install directory
2. Restarts Syllablaze

**Note:** Only updates Python files, not dependencies or package structure.

### Full Reinstall

For package structure or dependency changes:

```bash
pipx uninstall syllablaze
python3 install.py
```

## Step 5: Code Quality

### Run Tests

```bash
# All tests
pytest

# Specific category
pytest -m audio
pytest -m ui

# With coverage
pytest --cov=blaze --cov-report=html
```

### Linting

```bash
# Flake8 (required for CI)
flake8 . --max-line-length=127 --max-complexity=10

# Ruff (optional, faster)
ruff check blaze/ --fix
```

### Documentation

Build documentation locally:

```bash
mkdocs serve
# Visit http://localhost:8000
```

## Development Tools

### Recommended IDE Setup

- **VS Code:** Python extension, PyQt6 stubs
- **PyCharm:** PyQt6 support built-in

### Debugging

```bash
# Run with debug logging
python3 -m blaze.main --debug

# Qt debugging
export QT_DEBUG_PLUGINS=1
python3 -m blaze.main
```

### QML Development

```bash
# QML scene graph debugging
export QSG_INFO=1
python3 -m blaze.main
```

## Git Workflow

### Keeping Fork Updated

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Creating Pull Request

1. Push to your fork:
   ```bash
   git push origin feature/my-feature
   ```

2. Open PR on GitHub from your fork to `PabloVitasso/Syllablaze:main`

3. Fill PR template and pass CI checks

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed PR guidelines.

## Troubleshooting Development Setup

### Import errors

Ensure you're in the project root:
```bash
cd Syllablaze
python3 -m blaze.main
```

### Qt/PyQt6 issues

```bash
pip install --upgrade PyQt6
```

### Audio device errors in tests

Tests use mocks and don't require audio hardware. If tests fail:
```bash
pytest -v  # Verbose output for debugging
```

---

**Next Steps:**
- [Architecture Overview](architecture.md) - Understand the codebase
- [Testing Guide](testing.md) - Write and run tests
- [Patterns & Pitfalls](patterns-and-pitfalls.md) - Best practices
