#!/usr/bin/env python3
"""Test script to verify model registry and getAvailableModels works correctly."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

print("=" * 60)
print("Testing Model Registry")
print("=" * 60)

# Test 1: Import the registry
try:
    from blaze.backends.registry import ModelRegistry, UNIFIED_MODEL_REGISTRY

    print(f"✓ Successfully imported ModelRegistry")
    print(f"  Total models in registry: {len(UNIFIED_MODEL_REGISTRY)}")
except Exception as e:
    print(f"✗ Failed to import ModelRegistry: {e}")
    sys.exit(1)

# Test 2: Get all models
try:
    all_models = ModelRegistry.get_all_models()
    print(f"✓ get_all_models() returned {len(all_models)} models")
    if all_models:
        print(f"  First model: {all_models[0].model_id} ({all_models[0].name})")
except Exception as e:
    print(f"✗ get_all_models() failed: {e}")

# Test 3: Get models for language
try:
    en_models = ModelRegistry.get_models_for_language("en")
    print(f"✓ get_models_for_language('en') returned {len(en_models)} models")

    all_lang_models = ModelRegistry.get_models_for_language("all")
    print(f"✓ get_models_for_language('all') returned {len(all_lang_models)} models")
except Exception as e:
    print(f"✗ get_models_for_language() failed: {e}")

# Test 4: Get models for backend
try:
    whisper_models = ModelRegistry.get_models_for_backend("whisper")
    print(f"✓ get_models_for_backend('whisper') returned {len(whisper_models)} models")
except Exception as e:
    print(f"✗ get_models_for_backend() failed: {e}")

# Test 5: Import and test the coordinator
try:
    from blaze.backends.coordinator import get_coordinator

    coordinator = get_coordinator()
    print(f"✓ Successfully created coordinator")
    backends = coordinator.get_available_backends()
    print(f"  Available backends: {backends}")
except Exception as e:
    print(f"✗ Failed to create coordinator: {e}")

# Test 6: Test resource detection
try:
    from blaze.system.resource_detector import detect_resources

    resources = detect_resources()
    print(f"✓ Successfully detected resources")
    print(
        f"  RAM: {resources.total_ram_gb}GB total, {resources.available_ram_gb}GB available"
    )
    print(f"  GPU: {'Yes' if resources.gpu_available else 'No'}")
except Exception as e:
    print(f"✗ Failed to detect resources: {e}")

# Test 7: Test SettingsBridge.getAvailableModels
try:
    from blaze.settings import Settings
    from blaze.kirigami_integration import SettingsBridge

    # Create test settings
    settings = Settings()
    bridge = SettingsBridge(settings)

    print("\n" + "=" * 60)
    print("Testing SettingsBridge.getAvailableModels()")
    print("=" * 60)

    # Test with different filters
    for lang_filter, backend_filter in [
        ("all", "all"),
        ("en", "all"),
        ("all", "whisper"),
    ]:
        try:
            models = bridge.getAvailableModels(lang_filter, backend_filter)
            print(
                f"✓ getAvailableModels('{lang_filter}', '{backend_filter}') returned {len(models)} models"
            )
            if models:
                print(
                    f"  First model: {models[0].get('name', 'N/A')} ({models[0].get('id', 'N/A')})"
                )
            else:
                print(f"  WARNING: No models returned!")
        except Exception as e:
            print(
                f"✗ getAvailableModels('{lang_filter}', '{backend_filter}') failed: {e}"
            )
            import traceback

            traceback.print_exc()

except Exception as e:
    print(f"✗ Failed to test SettingsBridge: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
