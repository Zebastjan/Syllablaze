"""
Tests for the LockManager class

Tests cover:
- Lock acquisition and release
- Single-instance enforcement
- Stale lock detection and cleanup
- Directory creation
- Error handling and edge cases
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from blaze.managers.lock_manager import LockManager


@pytest.fixture
def temp_lock_path():
    """Create a temporary lock file path"""
    temp_dir = tempfile.mkdtemp()
    lock_path = os.path.join(temp_dir, 'test.lock')
    yield lock_path
    # Cleanup
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


@pytest.fixture
def lock_manager(temp_lock_path):
    """Create a LockManager instance for testing"""
    manager = LockManager(temp_lock_path)
    yield manager
    # Cleanup
    manager.release_lock()


def test_lock_manager_initialization(temp_lock_path):
    """Test LockManager initialization"""
    manager = LockManager(temp_lock_path)
    assert manager.lock_path == temp_lock_path
    assert manager.lock_file is None
    assert manager.lock_dir == os.path.dirname(temp_lock_path)


def test_ensure_lock_directory_creates_directory():
    """Test that ensure_lock_directory creates missing directory"""
    temp_dir = tempfile.mkdtemp()
    try:
        lock_path = os.path.join(temp_dir, 'subdir', 'test.lock')
        manager = LockManager(lock_path)

        # Directory shouldn't exist yet
        assert not os.path.exists(manager.lock_dir)

        # Call ensure_lock_directory
        result = manager.ensure_lock_directory()

        assert result is True
        assert os.path.exists(manager.lock_dir)
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_ensure_lock_directory_existing_directory(temp_lock_path):
    """Test ensure_lock_directory with existing directory"""
    manager = LockManager(temp_lock_path)
    # Directory already exists
    result = manager.ensure_lock_directory()
    assert result is True


def test_acquire_lock_success(lock_manager):
    """Test successful lock acquisition"""
    result = lock_manager.acquire_lock()
    assert result is True
    assert lock_manager.lock_file is not None
    assert os.path.exists(lock_manager.lock_path)

    # Verify PID was written to lock file
    with open(lock_manager.lock_path, 'r') as f:
        pid = f.read().strip()
        assert pid == str(os.getpid())


def test_acquire_lock_twice_fails(lock_manager):
    """Test that acquiring lock twice from same process succeeds first time"""
    # First acquisition should succeed
    result1 = lock_manager.acquire_lock()
    assert result1 is True

    # Create a second lock manager with same path
    manager2 = LockManager(lock_manager.lock_path)
    # Second acquisition should fail (lock is held)
    result2 = manager2.acquire_lock()
    assert result2 is False


def test_release_lock_success(lock_manager):
    """Test successful lock release"""
    # Acquire lock first
    lock_manager.acquire_lock()
    assert os.path.exists(lock_manager.lock_path)

    # Release lock
    result = lock_manager.release_lock()
    assert result is True
    assert lock_manager.lock_file is None
    assert not os.path.exists(lock_manager.lock_path)


def test_release_lock_when_not_acquired(lock_manager):
    """Test releasing lock when it wasn't acquired"""
    # Should succeed (no-op)
    result = lock_manager.release_lock()
    assert result is True


def test_stale_lock_cleanup(temp_lock_path):
    """Test that stale locks are cleaned up"""
    manager1 = LockManager(temp_lock_path)

    # Create a lock file with a fake PID that doesn't exist
    fake_pid = 99999
    os.makedirs(os.path.dirname(temp_lock_path), exist_ok=True)
    with open(temp_lock_path, 'w') as f:
        f.write(str(fake_pid))

    # Try to acquire lock - should clean up stale lock and succeed
    result = manager1.acquire_lock()
    assert result is True

    # Verify new PID was written
    with open(temp_lock_path, 'r') as f:
        pid = f.read().strip()
        assert pid == str(os.getpid())

    # Cleanup
    manager1.release_lock()


def test_lock_directory_creation_failure():
    """Test handling of lock directory creation failure"""
    # Use an invalid path that can't be created
    with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
        manager = LockManager('/invalid/path/test.lock')
        result = manager.ensure_lock_directory()
        assert result is False


def test_acquire_lock_with_directory_creation_failure():
    """Test lock acquisition when directory creation fails"""
    with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
        manager = LockManager('/invalid/path/test.lock')
        result = manager.acquire_lock()
        assert result is False


def test_acquire_lock_handles_exceptions():
    """Test that acquire_lock handles exceptions gracefully"""
    temp_dir = tempfile.mkdtemp()
    try:
        lock_path = os.path.join(temp_dir, 'test.lock')
        manager = LockManager(lock_path)

        # Mock fcntl.flock to raise an exception
        with patch('fcntl.flock', side_effect=IOError("Locking failed")):
            result = manager.acquire_lock()
            # Should handle exception and return False
            assert result is False
            assert manager.lock_file is None
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_release_lock_handles_exceptions():
    """Test that release_lock handles exceptions gracefully"""
    temp_dir = tempfile.mkdtemp()
    try:
        lock_path = os.path.join(temp_dir, 'test.lock')
        manager = LockManager(lock_path)
        manager.acquire_lock()

        # Mock fcntl.flock to raise an exception during release
        with patch('fcntl.flock', side_effect=Exception("Unlock failed")):
            result = manager.release_lock()
            # Should handle exception and return False
            assert result is False
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_concurrent_lock_acquisition():
    """Test that two LockManager instances can't hold same lock"""
    temp_dir = tempfile.mkdtemp()
    try:
        lock_path = os.path.join(temp_dir, 'test.lock')

        manager1 = LockManager(lock_path)
        manager2 = LockManager(lock_path)

        # First manager acquires lock
        result1 = manager1.acquire_lock()
        assert result1 is True

        # Second manager should fail to acquire same lock
        result2 = manager2.acquire_lock()
        assert result2 is False

        # Release first lock
        manager1.release_lock()

        # Now second manager should succeed
        result3 = manager2.acquire_lock()
        assert result3 is True

        # Cleanup
        manager2.release_lock()
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_lock_file_contains_pid(lock_manager):
    """Test that lock file contains the process PID"""
    lock_manager.acquire_lock()

    with open(lock_manager.lock_path, 'r') as f:
        content = f.read().strip()
        assert content == str(os.getpid())

    lock_manager.release_lock()


def test_lock_survives_multiple_acquire_attempts(temp_lock_path):
    """Test that once locked, multiple acquire attempts fail"""
    manager1 = LockManager(temp_lock_path)
    manager1.acquire_lock()

    # Create multiple managers trying to acquire same lock
    for i in range(5):
        manager = LockManager(temp_lock_path)
        result = manager.acquire_lock()
        assert result is False, f"Attempt {i} should have failed"

    # Cleanup
    manager1.release_lock()


def test_lock_path_is_absolute(temp_lock_path):
    """Test that lock manager works with absolute paths"""
    manager = LockManager(temp_lock_path)
    manager.acquire_lock()

    # Lock file should exist at the specified path
    assert os.path.exists(temp_lock_path)
    assert os.path.isabs(manager.lock_path)

    manager.release_lock()


def test_lock_cleanup_on_release(lock_manager):
    """Test that lock file is removed on release"""
    lock_manager.acquire_lock()
    lock_path = lock_manager.lock_path

    # Lock file should exist
    assert os.path.exists(lock_path)

    # Release lock
    lock_manager.release_lock()

    # Lock file should be removed
    assert not os.path.exists(lock_path)
