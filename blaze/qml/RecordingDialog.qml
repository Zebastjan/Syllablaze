import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: root
    title: "Syllablaze Recording"

    // Borderless window properties with transparency
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"

    // Circular window dimensions
    width: 200
    height: 200

    // Visible initially
    visible: true

    // Reduce opacity during transcription
    opacity: audioBridge.isTranscribing ? 0.5 : 1.0

    Behavior on opacity {
        NumberAnimation { duration: 200 }
    }

    // Circular background (only visible when recording)
    Rectangle {
        id: background
        anchors.fill: parent
        radius: width / 2
        color: audioBridge.isRecording ? "#232629" : "transparent"  // Dark background only when recording
        border.color: audioBridge.isRecording ? "#ef2929" : "transparent"  // Red border only when recording
        border.width: audioBridge.isRecording ? 2 : 0

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
        width: iconContainer.width + 60 + (audioBridge.currentVolume * 60)  // Grow with volume
        height: width
        radius: width / 2
        visible: audioBridge.isRecording

        // Color based on volume level
        // Green: 0-60% (good), Yellow: 60-85% (high), Red: 85-100% (peaking)
        property color volumeColor: {
            if (audioBridge.currentVolume < 0.6) {
                // Green for good range
                return Qt.rgba(0.2, 0.8, 0.2, 0.6 + audioBridge.currentVolume * 0.4)
            } else if (audioBridge.currentVolume < 0.85) {
                // Yellow/Orange for high
                return Qt.rgba(1.0, 0.7, 0.0, 0.7 + audioBridge.currentVolume * 0.3)
            } else {
                // Red for peaking
                return Qt.rgba(1.0, 0.2, 0.0, 0.8 + audioBridge.currentVolume * 0.2)
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
        border.width: 2 + (audioBridge.currentVolume * 3)  // 2-5px based on volume
        border.color: volumeVisualization.volumeColor
        visible: audioBridge.isRecording

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
        scale: audioBridge.isRecording ? 1.1 : 1.0

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
        visible: audioBridge.isTranscribing

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

    // Mouse interaction handler
    MouseArea {
        id: mouseHandler
        anchors.fill: parent

        property point pressPos: Qt.point(0, 0)
        property bool wasDragged: false

        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

        onPressed: (mouse) => {
            pressPos = Qt.point(mouse.x, mouse.y)
            wasDragged = false

            // For left button, prepare for potential drag
            if (mouse.button === Qt.LeftButton) {
                // Don't start system move yet, wait to see if it's a click or drag
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
                // Use Qt's native window dragging
                root.startSystemMove()
            }
        }

        onReleased: (mouse) => {
            if (!wasDragged) {
                // It was a click, not a drag
                if (mouse.button === Qt.LeftButton) {
                    console.log("Left click - toggle recording")
                    dialogBridge.toggleRecording()
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
            wasDragged = false
        }

        // Double-click to dismiss
        onDoubleClicked: {
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
            text: audioBridge.isRecording ? "Stop Recording" : "Start Recording"
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
            onTriggered: dialogBridge.dismissDialog()
        }
    }

    // Window behavior
    Component.onCompleted: {
        console.log("RecordingDialog: Window created")

        // Center window on screen
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

                console.log("Target position:", centerX, ",", centerY)

                root.x = Math.max(0, centerX)
                root.y = Math.max(0, centerY)
                console.log("RecordingDialog: Position set to", root.x, ",", root.y)
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

    // Close handling
    onClosing: {
        console.log("RecordingDialog: Window closing")
        dialogBridge.dialogClosed()
    }
}
