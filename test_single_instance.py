#!/usr/bin/env python3

import os
import sys
import time
import fcntl

# Lock file path
LOCK_FILE_PATH = os.path.expanduser("~/.cache/syllablaze/syllablaze.lock")
LOCK_FILE = None

def check_already_running():
    """Check if an instance is already running using a file lock mechanism"""
    global LOCK_FILE
    
    # Create directory if it doesn't exist
    lock_dir = os.path.dirname(LOCK_FILE_PATH)
    if not os.path.exists(lock_dir):
        try:
            os.makedirs(lock_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create lock directory: {e}")
            return False
    
    try:
        # Check if the lock file exists
        if os.path.exists(LOCK_FILE_PATH):
            try:
                # Try to open the existing lock file for reading and writing
                test_lock = open(LOCK_FILE_PATH, 'r+')
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
                            print(f"Found process {pid} but lock file wasn't locked. Assuming stale lock.")
                        except OSError:
                            # Process doesn't exist
                            print(f"Removing stale lock file for PID {pid}")
                    
                    # Release the lock and close the file
                    fcntl.flock(test_lock, fcntl.LOCK_UN)
                    test_lock.close()
                    
                    # Remove the stale lock file
                    os.remove(LOCK_FILE_PATH)
                except IOError:
                    # The file is locked by another process
                    test_lock.close()
                    print("Lock file is locked by another process")
                    return True
            except Exception as e:
                print(f"Error checking existing lock file: {e}")
                # If we can't read the lock file, try to remove it
                try:
                    os.remove(LOCK_FILE_PATH)
                except:
                    pass
        
        # Create a new lock file
        LOCK_FILE = open(LOCK_FILE_PATH, 'w')
        # Write PID to the file
        LOCK_FILE.write(str(os.getpid()))
        LOCK_FILE.flush()
        # Log the lock file path for debugging
        print(f"INFO: Lock file created at: {os.path.abspath(LOCK_FILE_PATH)}")
        
        try:
            # Try to get an exclusive lock
            fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
            print(f"Acquired lock file for PID {os.getpid()}")
            return False
        except IOError:
            # This shouldn't happen since we just created the file,
            # but handle it just in case
            print("Failed to acquire lock on newly created file")
            LOCK_FILE.close()
            LOCK_FILE = None
            return True
    except IOError as e:
        # Lock already held by another process
        print(f"Lock already held by another process: {e}")
        if LOCK_FILE:
            LOCK_FILE.close()
            LOCK_FILE = None
        return True
    except Exception as e:
        print(f"Error in file locking mechanism: {e}")
        # Fall back to process-based check if file locking fails
        if LOCK_FILE:
            LOCK_FILE.close()
            LOCK_FILE = None
        return False

def cleanup_lock_file():
    """Clean up lock file when application exits"""
    global LOCK_FILE
    if LOCK_FILE:
        try:
            # Release the lock
            fcntl.flock(LOCK_FILE, fcntl.LOCK_UN)
            LOCK_FILE.close()
            # Remove the lock file
            if os.path.exists(LOCK_FILE_PATH):
                os.remove(LOCK_FILE_PATH)
            LOCK_FILE = None
            print("Released application lock file")
        except Exception as e:
            print(f"Error releasing lock file: {e}")

def main():
    """Main function"""
    print(f"Process ID: {os.getpid()}")
    
    # Check if already running
    if check_already_running():
        print("Another instance is already running. Only one instance is allowed.")
        return 1
    
    try:
        # Simulate the application running
        print("Application is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Clean up lock file
        cleanup_lock_file()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())