#!/usr/bin/env python3
"""Test the RecordingDialog with full state changes"""

import sys
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
    else:
        print("✗ Failed to create dialog window")
        return 1

    # Connect signals
    def on_toggle():
        print("→ Toggle recording requested from dialog")

    def on_clipboard():
        print("→ Open clipboard requested from dialog")

    def on_settings():
        print("→ Open settings requested from dialog")

    dialog.dialog_bridge.toggleRecordingRequested.connect(on_toggle)
    dialog.dialog_bridge.openClipboardRequested.connect(on_clipboard)
    dialog.dialog_bridge.openSettingsRequested.connect(on_settings)

    print("Showing dialog...")
    dialog.show()

    # Simulate recording workflow
    step = 0

    def simulate_workflow():
        nonlocal step
        step += 1

        if step == 1:
            print("\n=== Step 1: Start recording ===")
            dialog.update_recording_state(True)

        elif step == 2:
            print("\n=== Step 2: Simulate volume changes ===")
            import random
            for _ in range(5):
                volume = random.random()
                dialog.update_volume(volume)
                print(f"  Volume: {volume:.2f}")

        elif step == 3:
            print("\n=== Step 3: Stop recording, start transcribing ===")
            dialog.update_recording_state(False)
            dialog.update_transcribing_state(True)

        elif step == 4:
            print("\n=== Step 4: Finish transcribing ===")
            dialog.update_transcribing_state(False)

        elif step == 5:
            print("\n=== Step 5: Hide dialog ===")
            dialog.hide()

        elif step == 6:
            print("\n=== Step 6: Show dialog again ===")
            dialog.show()

        elif step == 7:
            print("\n=== Test complete, exiting ===")
            app.quit()

    timer = QTimer()
    timer.timeout.connect(simulate_workflow)
    timer.start(1500)  # Every 1.5 seconds

    print("\nStarting simulation...")
    print("Watch the dialog window for visual changes")

    result = app.exec()
    print(f"\nApp exited with code: {result}")
    return result

if __name__ == "__main__":
    sys.exit(main())
