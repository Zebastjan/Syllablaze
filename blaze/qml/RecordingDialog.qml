import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: root
    title: "Syllablaze Recording"

    // Borderless window properties with transparency
    // Flags will be set from Python based on settings (not hardcoded here)
    color: "transparent"

    // Circular window dimensions
    width: 200
    height: 200

    // Start hidden - Python will show if needed
    visible: false

    // Track position changes in QML
    onXChanged: {
        if (root.visible && Qt.platform.os !== "windows") {
            // Only save position for frameless windows after they're shown
            // Delay to avoid saving during initial positioning
            console.log("onXChanged fired, x=" + root.x + ", restarting timer")
            positionSaveTimer.restart()
        }
    }

    onYChanged: {
        if (root.visible && Qt.platform.os !== "windows") {
            console.log("onYChanged fired, y=" + root.y + ", restarting timer")
            positionSaveTimer.restart()
        }
    }

    // Debounce position saving (don't save on every pixel move)
    Timer {
        id: positionSaveTimer
        interval: 500  // Save 500ms after user stops moving window
        onTriggered: {
            console.log("positionSaveTimer triggered, saving position (" + root.x + ", " + root.y + ")")
            dialogBridge.saveWindowPosition(root.x, root.y)
        }
    }

    // Delayed save for after drag completes (gives properties time to update)
    Timer {
        id: dragEndSaveTimer
        interval: 500  // Delay after drag ends for window manager to update position
        onTriggered: {
            console.log("dragEndSaveTimer triggered, saving position (" + root.x + ", " + root.y + ")")
            dialogBridge.saveWindowPosition(root.x, root.y)
        }
    }

    // Reduce opacity during transcription
    opacity: (dialogBridge && dialogBridge.isTranscribing) ? 0.5 : 1.0

    Behavior on opacity {
        NumberAnimation { duration: 200 }
    }

    // Circular background (only visible when recording)
    Rectangle {
        id: background
        anchors.fill: parent
        radius: width / 2
        color: (dialogBridge && dialogBridge.isRecording) ? "#232629" : "transparent"  // Dark background only when recording
        border.color: (dialogBridge && dialogBridge.isRecording) ? "#ef2929" : "transparent"  // Red border only when recording
        border.width: (dialogBridge && dialogBridge.isRecording) ? 2 : 0

        Behavior on color {
            ColorAnimation { duration: 200 }
        }

        Behavior on border.color {
            ColorAnimation { duration: 200 }
        }

        Behavior on border.width {
            NumberAnimation { duration: 200 }
        }
    }

    // Radial gradient volume visualization (only visible when recording)
    Rectangle {
        id: volumeVisualization
        anchors.centerIn: parent
        width: iconContainer.width + 60 + ((dialogBridge ? dialogBridge.currentVolume : 0) * 60)  // Grow with volume
        height: width
        radius: width / 2
        visible: dialogBridge && dialogBridge.isRecording

        // Color based on volume level
        // Green: 0-60% (good), Yellow: 60-85% (high), Red: 85-100% (peaking)
        property color volumeColor: {
            var volume = dialogBridge ? dialogBridge.currentVolume : 0
            if (volume < 0.6) {
                // Green for good range
                return Qt.rgba(0.2, 0.8, 0.2, 0.6 + volume * 0.4)
            } else if (volume < 0.85) {
                // Yellow/Orange for high
                return Qt.rgba(1.0, 0.7, 0.0, 0.7 + volume * 0.3)
            } else {
                // Red for peaking
                return Qt.rgba(1.0, 0.2, 0.0, 0.8 + volume * 0.2)
            }
        }

        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: Qt.rgba(0, 0, 0, 0)  // Transparent center
            }
            GradientStop {
                position: 0.7
                color: Qt.rgba(0, 0, 0, 0)  // Transparent most of the way
            }
            GradientStop {
                position: 0.85
                color: volumeVisualization.volumeColor
            }
            GradientStop {
                position: 1.0
                color: volumeVisualization.volumeColor
            }
        }

        Behavior on width {
            NumberAnimation { duration: 80; easing.type: Easing.OutCubic }
        }

        Behavior on volumeColor {
            ColorAnimation { duration: 100 }
        }
    }

    // Outer ring for additional visual feedback
    Rectangle {
        id: outerRing
        anchors.centerIn: parent
        width: volumeVisualization.width + 8
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 2 + ((dialogBridge ? dialogBridge.currentVolume : 0) * 3)  // 2-5px based on volume
        border.color: volumeVisualization.volumeColor
        visible: dialogBridge && dialogBridge.isRecording

        Behavior on width {
            NumberAnimation { duration: 80; easing.type: Easing.OutCubic }
        }

        Behavior on border.width {
            NumberAnimation { duration: 80 }
        }

        Behavior on border.color {
            ColorAnimation { duration: 100 }
        }
    }

    // Application icon (microphone) with circular clipping container
    Item {
        id: iconContainer
        anchors.centerIn: parent
        width: 100
        height: 100

        // Scale animation when recording
        scale: (dialogBridge && dialogBridge.isRecording) ? 1.1 : 1.0

        Behavior on scale {
            NumberAnimation { duration: 200 }
        }

        // Circular mask container
        Rectangle {
            id: iconMask
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            clip: true

            Image {
                id: appIcon
                anchors.centerIn: parent
                width: parent.width
                height: parent.height
                source: "file:///home/zebastjan/syllablaze/resources/syllablaze.png"
                fillMode: Image.PreserveAspectFit
            }
        }
    }

    // Transcription overlay (shown when transcribing)
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: Qt.rgba(0, 0, 0, 0.6)
        visible: dialogBridge && dialogBridge.isTranscribing

        Label {
            anchors.centerIn: parent
            text: "Transcribing..."
            color: "white"
            font.pointSize: 10
        }

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }
    }

    // Timer to distinguish single-click from double-click
    Timer {
        id: clickTimer
        interval: 250  // Wait 250ms to see if it's a double-click
        onTriggered: {
            // This is a confirmed single-click
            console.log("Single click confirmed - toggle recording")
            dialogBridge.toggleRecording()
        }
    }

    // Timer to prevent accidental clicks when dialog appears
    Timer {
        id: showDelayTimer
        interval: 300  // Ignore clicks for 300ms after showing
        property bool ignoreClicks: false
        onTriggered: {
            ignoreClicks = false
        }
    }



    // Mouse interaction handler
    MouseArea {
        id: mouseHandler
        anchors.fill: parent

        property point pressPos: Qt.point(0, 0)
        property bool wasDragged: false
        property bool isDoubleClickSequence: false

        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

        onPressed: (mouse) => {
            pressPos = Qt.point(mouse.x, mouse.y)
            wasDragged = false

            // On double-click, Qt fires: pressed -> released -> pressed -> doubleClicked -> released
            // So we detect the second press and cancel any pending single-click
            if (mouse.button === Qt.LeftButton && clickTimer.running) {
                console.log("Second press detected - canceling single-click timer and marking as double-click sequence")
                clickTimer.stop()
                isDoubleClickSequence = true
            } else if (mouse.button === Qt.LeftButton) {
                // First click in potential sequence - reset flag
                isDoubleClickSequence = false
            }
        }

        onPositionChanged: (mouse) => {
            // Calculate distance moved
            var dx = mouse.x - pressPos.x
            var dy = mouse.y - pressPos.y
            var distance = Math.sqrt(dx * dx + dy * dy)

            // If moved more than 5 pixels with left button, start system drag
            if (distance > 5 && !wasDragged && mouse.buttons & Qt.LeftButton) {
                wasDragged = true
                console.log("Drag started (distance=" + distance + ")")
                // Use Qt's native window dragging
                root.startSystemMove()
            }
        }

        onReleased: (mouse) => {
            console.log("onReleased: wasDragged=" + wasDragged + ", button=" + mouse.button + ", clickTimer.running=" + clickTimer.running)
            
            // Ignore clicks if we just became visible
            if (showDelayTimer.ignoreClicks) {
                console.log("Click ignored - dialog just appeared")
                wasDragged = false
                return
            }

            if (wasDragged) {
                // Drag completed - save position
                // Note: startSystemMove() doesn't always trigger onXChanged/onYChanged
                // Use delayed save to ensure properties have updated
                console.log("Drag completed, scheduling delayed save")
                dragEndSaveTimer.restart()
                wasDragged = false
            } else {
                // It was a click, not a drag
                if (mouse.button === Qt.LeftButton) {
                    // Don't restart timer if this is part of a double-click sequence
                    if (!isDoubleClickSequence) {
                        // Start timer for single-click detection
                        clickTimer.restart()
                        console.log("Starting click timer for single-click detection")
                    } else {
                        console.log("Suppressing click timer - this was a double-click sequence")
                        isDoubleClickSequence = false  // Reset flag for next interaction
                    }
                }
                else if (mouse.button === Qt.MiddleButton) {
                    console.log("Middle click - open clipboard")
                    dialogBridge.openClipboard()
                }
                else if (mouse.button === Qt.RightButton) {
                    console.log("Right click - show context menu")
                    contextMenu.popup()
                }
            }
        }

        // Double-click to dismiss
        onDoubleClicked: (mouse) => {
            // Timer should already be stopped by the second onPressed
            // But stop it again just to be sure
            clickTimer.stop()
            console.log("Double-click - dismiss dialog")
            dialogBridge.dismissDialog()
        }

        // Scroll wheel for resizing
        onWheel: (wheel) => {
            var delta = wheel.angleDelta.y
            var sizeChange = delta > 0 ? 20 : -20

            var newSize = Math.max(100, Math.min(500, root.width + sizeChange))
            console.log("Scroll resize:", root.width, "->", newSize)

            root.width = newSize
            root.height = newSize
        }
    }

    // Context menu
    Menu {
        id: contextMenu

        MenuItem {
            text: (dialogBridge && dialogBridge.isRecording) ? "Stop Recording" : "Start Recording"
            onTriggered: dialogBridge.toggleRecording()
        }

        MenuItem {
            text: "Open Clipboard"
            onTriggered: dialogBridge.openClipboard()
        }

        MenuItem {
            text: "Settings"
            onTriggered: dialogBridge.openSettings()
        }

        MenuSeparator {}

        MenuItem {
            text: "Dismiss"
            onTriggered: {
                console.log("Dismiss menu clicked - saving position")
                dialogBridge.saveWindowPosition(root.x, root.y)
                dialogBridge.dismissDialog()
            }
        }
    }

    // Window behavior
    Component.onCompleted: {
        console.log("RecordingDialog: Window created")

        // Center window on screen (position saving is disabled on KDE/Wayland)
        var screens = Qt.application.screens
        console.log("Number of screens:", screens ? screens.length : "none")

        if (screens && screens.length > 0) {
            var screen = screens[0]
            console.log("Primary screen:", screen)

            if (screen && screen.availableGeometry) {
                var screenRect = screen.availableGeometry
                console.log("Screen geometry:", screenRect.width, "x", screenRect.height, "at", screenRect.x, ",", screenRect.y)

                var centerX = screenRect.x + (screenRect.width - root.width) / 2
                var centerY = screenRect.y + (screenRect.height - root.height) / 2

                console.log("Centering at:", centerX, ",", centerY)

                root.x = Math.max(0, centerX)
                root.y = Math.max(0, centerY)
                console.log("RecordingDialog: Centered at", root.x, ",", root.y)
            } else {
                console.log("No screen geometry available, using default position")
                root.x = 100
                root.y = 100
            }
        } else {
            console.log("No screens available, using default position")
            root.x = 100
            root.y = 100
        }
    }

    // Visibility change handling - save position when hiding
    onVisibleChanged: {
        if (!visible) {
            // Dialog is being hidden - save position
            // On Wayland, position is always 0,0 to the app, so only save on X11
            var isWayland = Qt.platform.os === "linux" && typeof dialogBridge !== 'undefined' && dialogBridge.isWayland ? dialogBridge.isWayland() : false
            if (!isWayland && root.x !== 0 && root.y !== 0) {
                console.log("Dialog hiding - saving position (" + root.x + ", " + root.y + ")")
                dialogBridge.saveWindowPosition(root.x, root.y)
            } else {
                console.log("Dialog hiding - skipping position save (Wayland or position 0,0)")
            }
        } else {
            // Dialog shown - ignoring clicks for 300ms
            showDelayTimer.ignoreClicks = true
            showDelayTimer.restart()
            console.log("Dialog shown - ignoring clicks for 300ms")
        }
    }

    // Close handling
    onClosing: {
        console.log("RecordingDialog: Window closing - saving position (" + root.x + ", " + root.y + ")")
        dialogBridge.saveWindowPosition(root.x, root.y)
        dialogBridge.dialogClosed()
    }
}
