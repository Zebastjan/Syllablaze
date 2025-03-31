"""
Lock Manager for Syllablaze

This module provides a centralized manager for lock file operations,
reducing code duplication and improving maintainability.
"""

import os
import logging

logger = logging.getLogger(__name__)

class LockManager:
    """Manager class for lock file operations"""
    
    def __init__(self, lock_path):
        """Initialize the lock manager
        
        Parameters:
        -----------
        lock_path : str
            Path to the lock file
        """
        self.lock_path = lock_path
        self.lock_file = None
        self.lock_dir = os.path.dirname(lock_path)
    
    def ensure_lock_directory(self):
        """Ensure the lock directory exists
        
        Returns:
        --------
        bool
            True if directory exists or was created, False otherwise
        """
        if not os.path.exists(self.lock_dir):
            try:
                os.makedirs(self.lock_dir, exist_ok=True)
                return True
            except Exception as e:
                logger.error(f"Failed to create lock directory: {e}")
                return False
        return True
    
    def acquire_lock(self):
        """Acquire a lock file
        
        Returns:
        --------
        bool
            True if lock was acquired, False if another instance is running
        """
        # Ensure lock directory exists
        if not self.ensure_lock_directory():
            return False
        
        try:
            import fcntl
            
            # Check if the lock file exists
            if os.path.exists(self.lock_path):
                try:
                    # Try to open the existing lock file for reading and writing
                    test_lock = open(self.lock_path, 'r+')
                    try:
                        # Try to get a non-blocking exclusive lock
                        fcntl.flock(test_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        
                        # If we got here, the file wasn't locked
                        # Read the PID from the file
                        test_lock.seek(0)
                        pid = test_lock.read().strip()
                        
                        # Check if the process with this PID is still running
                        if pid and pid.isdigit():
                            try:
                                # If we can send signal 0 to the process, it exists
                                os.kill(int(pid), 0)
                                # This is strange - the file exists and the process exists,
                                # but the file wasn't locked. This could happen if the process
                                # crashed without cleaning up. Let's assume it's not running.
                                logger.warning(f"Found process {pid} but lock file wasn't locked. Assuming stale lock.")
                            except OSError:
                                # Process doesn't exist
                                logger.info(f"Removing stale lock file for PID {pid}")
                        
                        # Release the lock and close the file
                        fcntl.flock(test_lock, fcntl.LOCK_UN)
                        test_lock.close()
                        
                        # Remove the stale lock file
                        os.remove(self.lock_path)
                    except IOError:
                        # The file is locked by another process
                        test_lock.close()
                        logger.info("Lock file is locked by another process")
                        return False
                except Exception as e:
                    logger.error(f"Error checking existing lock file: {e}")
                    # If we can't read the lock file, try to remove it
                    try:
                        os.remove(self.lock_path)
                    except Exception:
                        pass
            
            # Create a new lock file
            self.lock_file = open(self.lock_path, 'w')
            # Write PID to the file
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            # Log the lock file path for debugging
            logger.info(f"INFO: Lock file created at: {os.path.abspath(self.lock_path)}")
            
            try:
                # Try to get an exclusive lock
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.info(f"Acquired lock file for PID {os.getpid()}")
                return True
            except IOError:
                # This shouldn't happen since we just created the file,
                # but handle it just in case
                logger.error("Failed to acquire lock on newly created file")
                self.lock_file.close()
                self.lock_file = None
                return False
        except Exception as e:
            logger.error(f"Error in file locking mechanism: {e}")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False
    
    def release_lock(self):
        """Release the lock file
        
        Returns:
        --------
        bool
            True if lock was released, False otherwise
        """
        if not self.lock_file:
            return True
            
        try:
            import fcntl
            # Release the lock
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            # Remove the lock file
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
            self.lock_file = None
            logger.info("Released application lock file")
            return True
        except Exception as e:
            logger.error(f"Error releasing lock file: {e}")
            return False
    
    def check_already_running_by_process(self):
        """Check if application is already running by process name
        
        Returns:
        --------
        bool
            True if another instance is running, False otherwise
        """
        try:
            import psutil
            current_pid = os.getpid()
            count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check if this is a Python process
                    if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                        # Check if it's running syllablaze
                        cmdline = proc.info['cmdline']
                        if cmdline and any('syllablaze' in cmd for cmd in cmdline):
                            # Don't count the current process
                            if proc.info['pid'] != current_pid:
                                count += 1
                                logger.info(f"Found existing Syllablaze process: PID {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            return count > 0
        except Exception as e:
            logger.error(f"Error checking for running processes: {e}")
            return False