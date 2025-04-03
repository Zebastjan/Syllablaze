# tests/README.md - Documentation for Syllablaze Tests

This directory contains tests for the Syllablaze application.

## Test Structure

The tests are organized according to the following structure:

```
tests/
├── __init__.py
├── conftest.py            # Common fixtures and configuration
├── pytest.ini             # Pytest configuration
├── test_audio_processor.py  # Tests for audio processing
└── README.md              # This file
```

## Running Tests

To run all tests, from the project root directory:

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/test_audio_processor.py
```

To run a specific test function:

```bash
pytest tests/test_audio_processor.py::test_frames_to_numpy
```

## Test Categories

Tests are organized by markers:

- `unit`: Unit tests
- `integration`: Integration tests
- `audio`: Tests related to audio processing
- `ui`: Tests related to UI components
- `settings`: Tests related to settings management
- `core`: Tests related to core functionality

To run tests with a specific marker:

```bash
pytest -m audio
```

## Test Coverage

To run tests with coverage:

```bash
pytest --cov=blaze
```

To generate an HTML coverage report:

```bash
pytest --cov=blaze --cov-report=html
```

## Adding New Tests

When adding new tests:

1. Create a new file with the prefix `test_` (e.g., `test_new_feature.py`)
2. Add test functions with the prefix `test_` (e.g., `test_specific_functionality`)
3. Add appropriate markers to categorize your tests
4. Add fixtures to `conftest.py` if they can be reused across multiple test files

## Mocking Dependencies

Common mock objects for testing are available in `conftest.py`, including:

- `mock_pyaudio`: A mock PyAudio instance
- `mock_settings`: A mock Settings instance
- `sample_audio_frames`: Sample audio frames for testing
- `sine_wave_audio`: A sine wave audio sample

## Debugging Tests

Use the `--showlocals` flag to show local variables in tracebacks:

```bash
pytest --showlocals
```

Use `-v` for verbose output:

```bash
pytest -v
```