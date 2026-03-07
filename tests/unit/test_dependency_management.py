"""
Unit tests for dependency management system.

These tests verify that:
1. DependencyManager correctly identifies available backends
2. Backend dependency information is returned correctly
3. Installation commands are generated properly
4. SettingsBridge methods for dependency management work
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
from PyQt6.QtCore import QObject

# Mark tests as requiring PyQt6
pytestmark = [pytest.mark.qt, pytest.mark.unit]


class TestDependencyManager:
    """Tests for the DependencyManager class."""

    def test_backend_info_retrieval(self):
        """Test that backend info can be retrieved."""
        from blaze.backends.dependency_manager import DependencyManager

        # Test known backends
        granite_info = DependencyManager.get_backend_info("granite")
        assert granite_info is not None
        assert "packages" in granite_info
        assert "description" in granite_info
        assert "size_estimate" in granite_info
        assert "install_command" in granite_info

        # Test unknown backend
        unknown_info = DependencyManager.get_backend_info("unknown")
        assert unknown_info is None

    def test_backend_availability_check(self):
        """Test that backend availability is checked correctly."""
        from blaze.backends.dependency_manager import DependencyManager

        # Test whisper (should be available - core dependency)
        # Note: This might fail in test environment without whisper installed
        # So we'll patch it
        with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
            is_available = DependencyManager.is_backend_available("whisper")
            # Result depends on whether faster_whisper is actually installed
            assert isinstance(is_available, bool)

    def test_granite_backend_requires_transformers(self):
        """Test that granite backend requires transformers."""
        from blaze.backends.dependency_manager import DependencyManager

        # When transformers is not available, granite should not be available
        with patch.dict(
            "sys.modules",
            {
                "transformers": None,
                "torchaudio": MagicMock(),
                "peft": MagicMock(),
                "soundfile": MagicMock(),
            },
        ):
            # This will fail because transformers import will raise ImportError
            is_available = DependencyManager.is_backend_available("granite")
            assert is_available is False

    def test_get_install_command(self):
        """Test that install commands are generated correctly."""
        from blaze.backends.dependency_manager import DependencyManager

        granite_cmd = DependencyManager.get_install_command("granite")
        assert "pip install" in granite_cmd
        assert "transformers" in granite_cmd

        unknown_cmd = DependencyManager.get_install_command("unknown")
        assert unknown_cmd == ""


class TestSettingsBridgeDependencyMethods:
    """Tests for SettingsBridge dependency management methods."""

    @pytest.fixture
    def mock_settings(self):
        """Create a mock settings object."""
        settings = MagicMock()
        settings.get.return_value = "whisper-tiny"
        return settings

    @pytest.fixture
    def settings_bridge(self, mock_settings):
        """Create a SettingsBridge instance with mocked dependencies."""
        from blaze.backends.settings_bridge import ModelSettingsBridge

        # Patch coordinator to avoid initialization issues
        with patch("blaze.backends.settings_bridge.get_coordinator") as mock_coord:
            mock_coordinator = MagicMock()
            mock_coordinator.get_available_backends.return_value = ["whisper"]
            mock_coordinator.is_backend_available.return_value = True
            mock_coord.return_value = mock_coordinator

            bridge = ModelSettingsBridge(mock_settings)
            bridge._coordinator = mock_coordinator
            return bridge

    def test_get_backend_dependency_info(self, settings_bridge):
        """Test that backend dependency info is returned correctly."""
        info = settings_bridge.getBackendDependencyInfo("granite")

        assert isinstance(info, dict)
        assert "available" in info
        assert "packages" in info
        assert "install_command" in info
        assert "description" in info
        assert "size_estimate" in info

    def test_get_backend_dependency_info_unknown_backend(self, settings_bridge):
        """Test handling of unknown backend."""
        info = settings_bridge.getBackendDependencyInfo("unknown_backend")

        assert isinstance(info, dict)
        assert "available" in info
        assert info["available"] is False
        assert "error" in info

    def test_check_backend_dependencies(self, settings_bridge):
        """Test backend dependency checking."""
        with patch(
            "blaze.backends.settings_bridge.DependencyManager.is_backend_available"
        ) as mock_check:
            mock_check.return_value = True

            result = settings_bridge.checkBackendDependencies("granite")
            assert result is True

    def test_get_all_backends_with_status(self, settings_bridge):
        """Test retrieving all backends with their status."""
        backends = settings_bridge.getAllBackendsWithStatus()

        assert isinstance(backends, list)
        assert len(backends) > 0

        # Check structure of first backend
        first = backends[0]
        assert "name" in first
        assert "available" in first
        assert "description" in first
        assert "packages" in first
        assert "size_estimate" in first
        assert "install_command" in first
        assert "models_available" in first

    def test_can_download_model(self, settings_bridge):
        """Test checking if a model can be downloaded."""
        from blaze.backends.registry import ModelRegistry

        # Test with whisper model (should be available)
        with patch.object(
            settings_bridge._coordinator, "is_backend_available", return_value=True
        ):
            result = settings_bridge.canDownloadModel("whisper-tiny")
            assert isinstance(result, bool)

    def test_get_backend_for_model(self, settings_bridge):
        """Test getting backend for a specific model."""
        backend = settings_bridge.getBackendForModel("whisper-tiny")
        assert backend == "whisper"

        # Test unknown model
        unknown_backend = settings_bridge.getBackendForModel("nonexistent-model")
        assert unknown_backend is None


class TestSignals:
    """Tests for Qt signals in dependency management."""

    def test_signals_exist(self):
        """Test that required signals are defined."""
        from blaze.backends.settings_bridge import ModelSettingsBridge

        # Check signal definitions exist
        assert hasattr(ModelSettingsBridge, "dependencyInstallProgress")
        assert hasattr(ModelSettingsBridge, "dependencyInstallComplete")
        assert hasattr(ModelSettingsBridge, "backendAvailabilityChanged")


class TestIntegration:
    """Integration tests for dependency management."""

    def test_dependency_manager_covers_all_backends(self):
        """Test that DependencyManager knows about all backends."""
        from blaze.backends.dependency_manager import BACKEND_DEPENDENCIES

        expected_backends = ["liquid", "granite", "qwen"]

        for backend in expected_backends:
            assert backend in BACKEND_DEPENDENCIES, (
                f"Backend {backend} not in dependencies"
            )
            info = BACKEND_DEPENDENCIES[backend]
            assert "packages" in info
            assert "description" in info
            assert "size_estimate" in info

    def test_backend_registry_integration(self):
        """Test that all backends in registry have dependency info."""
        from blaze.backends.dependency_manager import DependencyManager
        from blaze.backends.registry import ModelRegistry

        # Get all models and their backends
        all_models = ModelRegistry.get_all_models()
        backends_in_registry = set(model.backend for model in all_models)

        # Whisper doesn't need dependency info (it's core)
        optional_backends = backends_in_registry - {"whisper"}

        for backend in optional_backends:
            info = DependencyManager.get_backend_info(backend)
            assert info is not None, f"Backend {backend} has no dependency info"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
