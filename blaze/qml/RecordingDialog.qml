import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: root
    title: "Syllablaze Recording"

    // Borderless window properties
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool

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

    // Circular background
    Rectangle {
        id: background
        anchors.fill: parent
        radius: width / 2
        color: "#232629"  // Dark background
        border.color: audioBridge.isRecording ? "#ef2929" : "#3daee9"  // Red when recording, KDE blue otherwise
        border.width: 2

        Behavior on border.color {
            ColorAnimation { duration: 200 }
        }
    }

    // Glowing volume ring (only visible when recording)
    Rectangle {
        id: volumeRing
        anchors.centerIn: parent
        width: iconContainer.width + 40 + (audioBridge.currentVolume * 40)  // Grow with volume
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 3 + (audioBridge.currentVolume * 10)  // 3-13px based on volume
        border.color: Qt.rgba(0.937, 0.161, 0.161, 0.3 + audioBridge.currentVolume * 0.7)  // Red with varying opacity
        visible: audioBridge.isRecording

        Behavior on border.width {
            NumberAnimation { duration: 100 }
        }

        Behavior on width {
            NumberAnimation { duration: 100 }
        }

        Behavior on border.color {
            ColorAnimation { duration: 100 }
        }
    }

    // Additional outer glow ring (simpler alternative to Glow effect)
    Rectangle {
        id: outerGlowRing
        anchors.centerIn: parent
        width: volumeRing.width + 10
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 2
        border.color: Qt.rgba(0.937, 0.161, 0.161, 0.2 + audioBridge.currentVolume * 0.3)
        visible: audioBridge.isRecording

        Behavior on width {
            NumberAnimation { duration: 100 }
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

        property point clickPos: Qt.point(0, 0)
        property bool isDragging: false

        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

        onPressed: (mouse) => {
            clickPos = Qt.point(mouse.x, mouse.y)
            isDragging = false
        }

        onPositionChanged: (mouse) => {
            // If moved more than threshold, it's a drag
            var dx = mouse.x - clickPos.x
            var dy = mouse.y - clickPos.y
            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                isDragging = true
                // Manual drag
                root.x += dx
                root.y += dy
            }
        }

        onReleased: (mouse) => {
            if (!isDragging) {
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
                    console.log("Right click - show settings menu")
                    contextMenu.popup()
                }
            }
            isDragging = false
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
