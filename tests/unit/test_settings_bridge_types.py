"""
Unit tests for SettingsBridge type conversion (critical for QML compatibility).
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blaze.kirigami_integration import SettingsBridge
from blaze.settings import Settings


class TestSettingsBridgeTypeConversion:
    """Test suite for SettingsBridge type conversion to QML."""

    @pytest.fixture
    def settings_bridge(self):
        """Create a SettingsBridge instance for testing."""
        settings = Settings()
        return SettingsBridge(settings)

    def test_get_available_models_returns_list(self, settings_bridge):
        """Test that getAvailableModels returns a list (not object)."""
        result = settings_bridge.getAvailableModels("all", "all")

        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) > 0, "Expected non-empty list"
        print(f"✓ getAvailableModels returned list with {len(result)} models")

    def test_model_dict_has_basic_types_only(self, settings_bridge):
        """Test that model dictionaries contain only basic Python types."""
        result = settings_bridge.getAvailableModels("all", "all")

        assert len(result) > 0, "No models returned"

        # Check first model
        model = result[0]
        assert isinstance(model, dict), f"Model is not a dict: {type(model)}"

        # Check all required fields and their types
        assert isinstance(model.get("id"), str), (
            f"id is not string: {type(model.get('id'))}"
        )
        assert isinstance(model.get("name"), str), (
            f"name is not string: {type(model.get('name'))}"
        )
        assert isinstance(model.get("backend"), str), (
            f"backend is not string: {type(model.get('backend'))}"
        )
        assert isinstance(model.get("description"), str), (
            f"description is not string: {type(model.get('description'))}"
        )
        assert isinstance(model.get("size"), str), (
            f"size is not string: {type(model.get('size'))}"
        )
        assert isinstance(model.get("sizeMB"), int), (
            f"sizeMB is not int: {type(model.get('sizeMB'))}"
        )
        assert isinstance(model.get("downloaded"), bool), (
            f"downloaded is not bool: {type(model.get('downloaded'))}"
        )
        assert isinstance(model.get("active"), bool), (
            f"active is not bool: {type(model.get('active'))}"
        )
        assert isinstance(model.get("compatible"), bool), (
            f"compatible is not bool: {type(model.get('compatible'))}"
        )
        assert isinstance(model.get("compatibility_reason"), str), (
            f"compatibility_reason is not string: {type(model.get('compatibility_reason'))}"
        )
        assert isinstance(model.get("recommended"), bool), (
            f"recommended is not bool: {type(model.get('recommended'))}"
        )
        assert isinstance(model.get("languages"), list), (
            f"languages is not list: {type(model.get('languages'))}"
        )
        assert isinstance(model.get("tier"), str), (
            f"tier is not string: {type(model.get('tier'))}"
        )

        # Check that languages contains only strings
        for lang in model.get("languages", []):
            assert isinstance(lang, str), (
                f"Language '{lang}' is not a string: {type(lang)}"
            )

        print(f"✓ All model fields are basic Python types")

    def test_get_hardware_info_returns_dict(self, settings_bridge):
        """Test that getHardwareInfo returns a dictionary."""
        result = settings_bridge.getHardwareInfo()

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check required fields
        assert "total_ram_gb" in result
        assert "available_ram_gb" in result
        assert "gpu_available" in result

        print(f"✓ getHardwareInfo returned dict with fields: {list(result.keys())}")

    def test_get_hardware_info_has_basic_types(self, settings_bridge):
        """Test that hardware info contains only basic types."""
        result = settings_bridge.getHardwareInfo()

        # Check numeric fields
        assert isinstance(result.get("total_ram_gb"), (int, float))
        assert isinstance(result.get("available_ram_gb"), (int, float))
        assert isinstance(result.get("cpu_count"), int)
        assert isinstance(result.get("gpu_available"), bool)
        assert isinstance(result.get("gpu_count"), int)

        # Check GPU lists if present
        if result.get("gpu_names"):
            assert isinstance(result.get("gpu_names"), list)
            for name in result.get("gpu_names"):
                assert isinstance(name, str)

        if result.get("gpu_memory_gb"):
            assert isinstance(result.get("gpu_memory_gb"), list)
            for mem in result.get("gpu_memory_gb"):
                assert isinstance(mem, (int, float))

        print(f"✓ Hardware info contains only basic types")

    def test_get_recommended_model_returns_dict(self, settings_bridge):
        """Test that getRecommendedModel returns a dictionary."""
        result = settings_bridge.getRecommendedModel()

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        print(f"✓ getRecommendedModel returned dict")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
