#!/usr/bin/env python3
"""Test the RecordingDialog QML loading"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from blaze.recording_dialog_manager import RecordingDialogManager

def main():
    app = QApplication(sys.argv)

    print("Creating RecordingDialogManager...")
    dialog = RecordingDialogManager()

    print("Initializing dialog...")
    dialog.initialize()

    if dialog.window:
        print("✓ Dialog window created successfully")
        print(f"  Window size: {dialog.window.property('width')}x{dialog.window.property('height')}")
    else:
        print("✗ Failed to create dialog window")
        return 1

    print("Showing dialog...")
    dialog.show()

    print("Setting up test volume updates...")
    # Test volume updates
    def update_volume():
        import random
        volume = random.random()
        dialog.update_volume(volume)
        print(f"  Volume: {volume:.2f}")

    timer = QTimer()
    timer.timeout.connect(update_volume)
    timer.start(500)

    print("Starting Qt event loop...")
    print("Close the dialog window to exit")

    # Exit after 5 seconds for automated testing
    QTimer.singleShot(5000, app.quit)

    result = app.exec()
    print(f"App exited with code: {result}")
    return result

if __name__ == "__main__":
    sys.exit(main())
