"""
Unit tests for model registry.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blaze.backends.registry import ModelRegistry, UNIFIED_MODEL_REGISTRY
from blaze.backends.base import ModelTier


class TestModelRegistry:
    """Test suite for ModelRegistry."""

    def test_get_all_models_returns_list(self):
        """Test that get_all_models returns a non-empty list."""
        models = ModelRegistry.get_all_models()
        assert isinstance(models, list)
        assert len(models) > 0
        print(f"✓ Registry contains {len(models)} models")

    def test_all_models_have_required_fields(self):
        """Test that all models have required fields."""
        models = ModelRegistry.get_all_models()
        required_fields = [
            "model_id",
            "name",
            "backend",
            "description",
            "size_mb",
            "min_ram_gb",
            "languages",
            "tier",
        ]

        for model in models:
            for field in required_fields:
                assert hasattr(model, field), (
                    f"Model {model.model_id} missing field: {field}"
                )
                value = getattr(model, field)
                assert value is not None, (
                    f"Model {model.model_id} has None for field: {field}"
                )

        print(f"✓ All {len(models)} models have required fields")

    def test_get_models_for_language(self):
        """Test filtering models by language."""
        # Test English
        en_models = ModelRegistry.get_models_for_language("en")
        assert isinstance(en_models, list)
        assert len(en_models) > 0

        # All returned models should support English
        for model in en_models:
            assert "en" in model.languages or "all" in model.languages, (
                f"Model {model.model_id} doesn't support English"
            )

        print(f"✓ Found {len(en_models)} models for English")

    def test_get_models_for_backend(self):
        """Test filtering models by backend."""
        whisper_models = ModelRegistry.get_models_for_backend("whisper")
        assert isinstance(whisper_models, list)
        assert len(whisper_models) > 0

        for model in whisper_models:
            assert model.backend == "whisper", (
                f"Model {model.model_id} has wrong backend: {model.backend}"
            )

        print(f"✓ Found {len(whisper_models)} Whisper models")

    def test_model_tier_is_enum_or_string(self):
        """Test that tier values are properly typed."""
        models = ModelRegistry.get_all_models()
        valid_tiers = ["ultra_light", "light", "medium", "heavy"]

        for model in models:
            if hasattr(model.tier, "value"):
                tier_value = model.tier.value
            else:
                tier_value = str(model.tier)

            assert tier_value in valid_tiers, (
                f"Model {model.model_id} has invalid tier: {tier_value}"
            )

        print(f"✓ All {len(models)} models have valid tier values")

    def test_get_model_by_id(self):
        """Test retrieving specific model by ID."""
        model = ModelRegistry.get_model("whisper-tiny")
        assert model is not None
        assert model.model_id == "whisper-tiny"
        assert model.name == "Whisper Tiny"
        print("✓ Successfully retrieved whisper-tiny model")

    def test_model_languages_is_list_of_strings(self):
        """Test that languages field is a list of strings."""
        models = ModelRegistry.get_all_models()

        for model in models:
            assert isinstance(model.languages, list), (
                f"Model {model.model_id}: languages is not a list"
            )
            assert len(model.languages) > 0, (
                f"Model {model.model_id}: languages list is empty"
            )
            for lang in model.languages:
                assert isinstance(lang, str), (
                    f"Model {model.model_id}: language '{lang}' is not a string"
                )

        print(f"✓ All {len(models)} models have valid language lists")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
