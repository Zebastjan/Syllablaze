#!/usr/bin/env python3

import os
import sys
import time
import fcntl

# Lock file path
LOCK_FILE_PATH = os.path.expanduser("~/.cache/syllablaze/syllablaze.lock")

def acquire_lock():
    """Try to acquire the lock file"""
    # Create directory if it doesn't exist
    lock_dir = os.path.dirname(LOCK_FILE_PATH)
    if not os.path.exists(lock_dir):
        try:
            os.makedirs(lock_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create lock directory: {e}")
            return None
    
    try:
        # Try to create and lock the file
        lock_file = open(LOCK_FILE_PATH, 'w')
        # Write PID to the file
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        # Log the lock file path for debugging
        print(f"INFO: Lock file created at: {os.path.abspath(LOCK_FILE_PATH)}")
        # Try to get an exclusive lock
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(f"Lock acquired by process {os.getpid()}")
        return lock_file
    except IOError:
        # Lock already held by another process
        print("Lock already held by another process")
        if lock_file:
            lock_file.close()
        return None
    except Exception as e:
        print(f"Error in file locking mechanism: {e}")
        if lock_file:
            lock_file.close()
        return None

def release_lock(lock_file):
    """Release the lock file"""
    if lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            # Remove the lock file
            if os.path.exists(LOCK_FILE_PATH):
                os.remove(LOCK_FILE_PATH)
            print("Lock released")
        except Exception as e:
            print(f"Error releasing lock file: {e}")

def main():
    """Main function"""
    print(f"Process ID: {os.getpid()}")
    
    # Try to acquire the lock
    lock_file = acquire_lock()
    if not lock_file:
        print("Failed to acquire lock. Another instance is likely running.")
        return 1
    
    try:
        # Hold the lock for a while
        print("Lock acquired. Holding for 10 seconds...")
        for i in range(10, 0, -1):
            print(f"Releasing in {i} seconds...")
            time.sleep(1)
    finally:
        # Release the lock
        release_lock(lock_file)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())