"""
Unit tests for transcription cancellation functionality

Tests the graceful cancellation of in-progress transcriptions to prevent
CTranslate2 semaphore leaks under high system load.
"""

import pytest
from unittest.mock import Mock, patch
from blaze.managers.transcription_manager import TranscriptionManager


@pytest.fixture
def mock_settings():
    """Create a mock settings object"""
    settings = Mock()
    settings.get = Mock(side_effect=lambda key, default=None: {
        'model': 'base',
        'language': 'auto',
        'beam_size': 5,
        'vad_filter': True,
        'word_timestamps': False
    }.get(key, default))
    settings.set = Mock()
    return settings


@pytest.fixture
def transcription_manager(mock_settings):
    """Create a TranscriptionManager instance"""
    manager = TranscriptionManager(mock_settings)
    return manager


class TestIsWorkerRunning:
    """Tests for is_worker_running() method"""

    def test_is_worker_running_no_transcriber(self, transcription_manager):
        """Returns False when no transcriber exists"""
        transcription_manager.transcriber = None
        assert transcription_manager.is_worker_running() is False

    def test_is_worker_running_no_worker(self, transcription_manager):
        """Returns False when transcriber exists but no worker"""
        transcription_manager.transcriber = Mock(spec=[])  # No worker attribute
        assert transcription_manager.is_worker_running() is False

    def test_is_worker_running_worker_not_running(self, transcription_manager):
        """Returns False when worker exists but not running"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=False)

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker

        assert transcription_manager.is_worker_running() is False

    def test_is_worker_running_worker_active(self, transcription_manager):
        """Returns True when worker is actively running"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=True)

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker

        assert transcription_manager.is_worker_running() is True


class TestCancelTranscription:
    """Tests for cancel_transcription() method"""

    def test_cancel_transcription_no_transcriber(self, transcription_manager):
        """Returns True when no transcriber exists"""
        transcription_manager.transcriber = None
        assert transcription_manager.cancel_transcription() is True

    def test_cancel_transcription_no_worker(self, transcription_manager):
        """Returns True when transcriber exists but no worker"""
        transcription_manager.transcriber = Mock()
        # Don't set worker attribute
        assert transcription_manager.cancel_transcription() is True

    def test_cancel_transcription_worker_not_running(self, transcription_manager):
        """Returns True when worker exists but not running"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=False)

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker

        assert transcription_manager.cancel_transcription() is True

    def test_cancel_transcription_graceful_quit(self, transcription_manager):
        """Cancellation uses quit() path when worker responds gracefully"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=True)
        mock_worker.quit = Mock()
        mock_worker.wait = Mock(return_value=True)  # Graceful quit succeeds
        mock_worker.terminate = Mock()  # Should NOT be called

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker
        transcription_manager.transcriber.model = Mock()

        with patch.object(transcription_manager, '_cleanup_worker_resources') as mock_cleanup:
            result = transcription_manager.cancel_transcription(timeout_ms=5000)

        assert result is True
        mock_worker.quit.assert_called_once()
        mock_worker.wait.assert_called_once_with(3000)  # 60% of 5000ms
        mock_worker.terminate.assert_not_called()  # Should not reach terminate phase
        mock_cleanup.assert_called_once()

    def test_cancel_transcription_forced_terminate(self, transcription_manager):
        """Cancellation uses terminate() when worker doesn't respond to quit"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=True)
        mock_worker.quit = Mock()
        mock_worker.wait = Mock(side_effect=[False, True])  # First wait fails, second succeeds
        mock_worker.terminate = Mock()

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker
        transcription_manager.transcriber.model = Mock()

        with patch.object(transcription_manager, '_cleanup_worker_resources') as mock_cleanup:
            result = transcription_manager.cancel_transcription(timeout_ms=5000)

        assert result is True
        mock_worker.quit.assert_called_once()
        assert mock_worker.wait.call_count == 2
        mock_worker.wait.assert_any_call(3000)  # 60% of 5000ms
        mock_worker.wait.assert_any_call(2000)  # 40% of 5000ms
        mock_worker.terminate.assert_called_once()
        mock_cleanup.assert_called_once()

    def test_cancel_transcription_custom_timeout(self, transcription_manager):
        """Respects custom timeout parameter"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=True)
        mock_worker.quit = Mock()
        mock_worker.wait = Mock(return_value=True)

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker
        transcription_manager.transcriber.model = Mock()

        with patch.object(transcription_manager, '_cleanup_worker_resources'):
            transcription_manager.cancel_transcription(timeout_ms=10000)

        # Should use 60% of 10000ms = 6000ms for graceful quit
        mock_worker.wait.assert_called_once_with(6000)

    def test_cancel_transcription_exception_handling(self, transcription_manager):
        """Returns False when exception occurs during cancellation"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=True)
        mock_worker.quit = Mock(side_effect=Exception("Test exception"))

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker

        result = transcription_manager.cancel_transcription()

        assert result is False


class TestCleanupWorkerResources:
    """Tests for _cleanup_worker_resources() helper"""

    def test_cleanup_worker_resources_releases_model(self, transcription_manager):
        """Verifies model reference is released"""
        mock_model = Mock()
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = mock_model

        with patch('gc.collect') as mock_gc:
            transcription_manager._cleanup_worker_resources()

        assert transcription_manager.transcriber.model is None
        mock_gc.assert_called()

    def test_cleanup_worker_resources_no_model(self, transcription_manager):
        """Handles case where model doesn't exist"""
        transcription_manager.transcriber = Mock()
        # Don't set model attribute

        with patch('gc.collect') as mock_gc:
            transcription_manager._cleanup_worker_resources()

        mock_gc.assert_called()

    def test_cleanup_worker_resources_cuda_available(self, transcription_manager):
        """Clears CUDA cache when CUDA is available"""
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = Mock()

        # Mock torch import inside the function
        mock_torch = Mock()
        mock_torch.cuda.is_available = Mock(return_value=True)
        mock_torch.cuda.empty_cache = Mock()
        mock_torch.cuda.synchronize = Mock()

        with patch('gc.collect'), \
             patch.dict('sys.modules', {'torch': mock_torch}):
            transcription_manager._cleanup_worker_resources()

            mock_torch.cuda.empty_cache.assert_called_once()
            mock_torch.cuda.synchronize.assert_called_once()

    def test_cleanup_worker_resources_no_cuda(self, transcription_manager):
        """Handles case where CUDA is not available"""
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = Mock()

        # Mock torch import inside the function
        mock_torch = Mock()
        mock_torch.cuda.is_available = Mock(return_value=False)
        mock_torch.cuda.empty_cache = Mock()

        with patch('gc.collect'), \
             patch.dict('sys.modules', {'torch': mock_torch}):
            transcription_manager._cleanup_worker_resources()

            # empty_cache should not be called when CUDA not available
            mock_torch.cuda.empty_cache.assert_not_called()

    def test_cleanup_worker_resources_no_torch(self, transcription_manager):
        """Handles case where torch is not installed"""
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = Mock()

        with patch('gc.collect'):
            # Remove torch from sys.modules to simulate ImportError
            import sys
            torch_backup = sys.modules.get('torch')
            try:
                if 'torch' in sys.modules:
                    del sys.modules['torch']
                # Should not raise exception
                transcription_manager._cleanup_worker_resources()
            finally:
                if torch_backup:
                    sys.modules['torch'] = torch_backup

    def test_cleanup_worker_resources_exception_handling(self, transcription_manager):
        """Handles exceptions gracefully during cleanup"""
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = Mock()

        # Make model assignment raise an exception
        with patch.object(
            transcription_manager.transcriber, 'model',
            new_callable=lambda: property(
                fget=lambda s: Mock(),
                fset=lambda s, v: (_ for _ in ()).throw(Exception("Test"))
            )
        ):
            # Should not raise exception
            transcription_manager._cleanup_worker_resources()


class TestCleanupRefactoring:
    """Tests for cleanup() method using cancel_transcription()"""

    def test_cleanup_calls_cancel_transcription(self, transcription_manager):
        """cleanup() calls cancel_transcription() when worker is running"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=True)

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker
        transcription_manager.transcriber.model = Mock()

        with patch.object(transcription_manager, 'cancel_transcription') as mock_cancel:
            mock_cancel.return_value = True
            transcription_manager.cleanup()

        mock_cancel.assert_called_once_with(timeout_ms=4000)

    def test_cleanup_skips_cancel_when_worker_not_running(self, transcription_manager):
        """cleanup() skips cancel_transcription() when worker not running"""
        mock_worker = Mock()
        mock_worker.isRunning = Mock(return_value=False)

        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.worker = mock_worker
        transcription_manager.transcriber.model = Mock()

        with patch.object(transcription_manager, 'cancel_transcription') as mock_cancel:
            transcription_manager.cleanup()

        mock_cancel.assert_not_called()
