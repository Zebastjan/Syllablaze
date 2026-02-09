# Development Workflow

## Branch Strategy

- **`main`** — Stable working code with PyQt6 settings UI and kglobalaccel shortcuts
- **`kirigami-rewrite`** — Development branch for Kirigami/QML settings UI rewrite

## Side-by-Side Testing

The updated `dev-update.sh` script automatically deploys to branch-specific packages:

| Branch | Package | Command |
|--------|---------|---------|
| `main` | `syllablaze` | `syllablaze` |
| `kirigami-rewrite` | `syllablaze-dev` | `syllablaze-dev` |

### Setup

1. **Install stable version** (from `main` branch):
   ```bash
   git checkout main
   pipx install -e .
   ```

2. **Install dev version** (from `kirigami-rewrite` branch):
   ```bash
   git checkout kirigami-rewrite
   pipx install -e . --suffix=-dev
   ```

### Daily Workflow

**Working on stable code:**
```bash
git checkout main
# make changes
./blaze/dev-update.sh  # deploys to syllablaze, runs syllablaze
```

**Working on Kirigami rewrite:**
```bash
git checkout kirigami-rewrite
# make changes
./blaze/dev-update.sh  # deploys to syllablaze-dev, runs syllablaze-dev
```

**Running both versions:**
```bash
syllablaze         # stable version
syllablaze-dev     # dev version
```

## Kirigami Development Tools

On the `kirigami-rewrite` branch:

```bash
# Test Kirigami integration
./blaze/qml_dev.sh test

# Live preview QML with hot-reload
./blaze/qml_dev.sh preview blaze/qml/TestSettings.qml

# List available QML files
./blaze/qml_dev.sh list

# Setup dev environment
./blaze/qml_dev.sh setup
```

## Linting

- **`main`** — ruff enabled with `--fix`
- **`kirigami-rewrite`** — ruff disabled during active development

```bash
# Manual lint (any branch)
flake8 . --max-line-length=127
ruff check blaze/ --fix
```

## Testing

```bash
pytest                                    # all tests
pytest tests/test_audio_processor.py      # specific file
pytest -m audio                           # by marker
```

## CI

GitHub Actions runs on push/PR to `main`:
- Python 3.10
- flake8 lint
- pytest

Dev branches can be pushed to origin but won't trigger CI unless merged to `main`.
