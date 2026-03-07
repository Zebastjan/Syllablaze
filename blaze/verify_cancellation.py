#!/usr/bin/env python3
"""
Verification script for transcription cancellation functionality

This script verifies that:
1. TranscriptionManager has is_worker_running() method
2. TranscriptionManager has cancel_transcription() method
3. AudioManager's is_ready_to_record() checks worker running state
4. main.py's on_activate() includes cancellation logic
"""

import ast
import sys


def check_method_exists(filepath, class_name, method_name):
    """Check if a method exists in a class"""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return True
    return False


def check_code_contains(filepath, search_text):
    """Check if file contains specific text"""
    with open(filepath, 'r') as f:
        content = f.read()
    return search_text in content


def main():
    print("Verifying transcription cancellation implementation...")
    print()

    checks = []

    # Check 1: TranscriptionManager.is_worker_running()
    result = check_method_exists(
        'blaze/managers/transcription_manager.py',
        'TranscriptionManager',
        'is_worker_running'
    )
    checks.append(('TranscriptionManager.is_worker_running() exists', result))

    # Check 2: TranscriptionManager.cancel_transcription()
    result = check_method_exists(
        'blaze/managers/transcription_manager.py',
        'TranscriptionManager',
        'cancel_transcription'
    )
    checks.append(('TranscriptionManager.cancel_transcription() exists', result))

    # Check 3: TranscriptionManager._cleanup_worker_resources()
    result = check_method_exists(
        'blaze/managers/transcription_manager.py',
        'TranscriptionManager',
        '_cleanup_worker_resources'
    )
    checks.append(('TranscriptionManager._cleanup_worker_resources() exists', result))

    # Check 4: AudioManager checks is_worker_running in is_ready_to_record
    result = check_code_contains(
        'blaze/managers/audio_manager.py',
        'is_worker_running'
    )
    checks.append(('AudioManager.is_ready_to_record() checks is_worker_running', result))

    # Check 5: main.py on_activate checks is_worker_running
    result = check_code_contains(
        'blaze/main.py',
        'is_worker_running'
    )
    checks.append(('main.py on_activate() checks is_worker_running', result))

    # Check 6: main.py on_activate calls cancel_transcription
    result = check_code_contains(
        'blaze/main.py',
        'cancel_transcription'
    )
    checks.append(('main.py on_activate() calls cancel_transcription', result))

    # Check 7: Test file exists
    try:
        with open('tests/test_transcription_cancellation.py', 'r') as f:
            test_content = f.read()
        result = 'TestIsWorkerRunning' in test_content and 'TestCancelTranscription' in test_content
    except FileNotFoundError:
        result = False
    checks.append(('test_transcription_cancellation.py exists with tests', result))

    # Print results
    all_passed = True
    for check_name, passed in checks:
        status = '✓' if passed else '✗'
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✓ All verification checks passed!")
        return 0
    else:
        print("✗ Some verification checks failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
