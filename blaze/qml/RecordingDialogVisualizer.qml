/*
    RecordingDialogVisualizer.qml - SVG Element Targeting Implementation
    
    Uses SvgRendererBridge to get precise element bounds from syllablaze.svg:
    - status_indicator: Area for status color overlay
    - waveform: Area for visualization drawing
*/

import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: root
    
    title: "Syllablaze Recording"
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    
    width: 200
    height: 200
    minimumWidth: 100
    minimumHeight: 100
    maximumWidth: 500
    maximumHeight: 500
    
    visible: false
    
    // Properties from bridges
    property bool isRecording: dialogBridge ? dialogBridge.isRecording : false
    property real currentVolume: dialogBridge ? dialogBridge.currentVolume : 0.0
    property var audioSamples: dialogBridge ? dialogBridge.audioSamples : []
    property bool isTranscribing: dialogBridge ? dialogBridge.isTranscribing : false
    
    // SVG element bounds (mapped to widget coordinates)
    property rect inputLevelBounds: svgBridge ? mapSvgRectToWidget(svgBridge.inputLevelBounds) : Qt.rect(0, 0, width, height)
    property rect waveformBounds: svgBridge ? mapSvgRectToWidget(svgBridge.waveformBounds) : Qt.rect(0, 0, width, height)
    property rect activeAreaBounds: svgBridge ? mapSvgRectToWidget(svgBridge.activeAreaBounds) : Qt.rect(0, 0, width, height)
    property real viewBoxWidth: svgBridge ? svgBridge.viewBoxWidth : 512
    property real viewBoxHeight: svgBridge ? svgBridge.viewBoxHeight : 512
    
    // Helper function to map SVG rect to widget coordinates
    function mapSvgRectToWidget(svgRect) {
        if (!svgRect) return Qt.rect(0, 0, width, height)
        
        var scaleX = width / viewBoxWidth
        var scaleY = height / viewBoxHeight
        
        return Qt.rect(
            svgRect.x * scaleX,
            svgRect.y * scaleY,
            svgRect.width * scaleX,
            svgRect.height * scaleY
        )
    }
    
    // Helper function to get status color
    function getStatusColor() {
        if (!isRecording) return "#3498db"
        
        // Amplify volume for better visualization (input is often very quiet)
        var displayVolume = Math.min(1.0, currentVolume * 10)
        
        if (displayVolume < 0.5) {
            var t = displayVolume * 2
            return Qt.rgba(0.2 + (t * 0.8), 0.8, 0.2, 1.0)
        } else {
            var t = (displayVolume - 0.5) * 2
            return Qt.rgba(1.0, 0.8 - (t * 0.8), 0.2, 1.0)
        }
    }
    
    // Main container
    Item {
        anchors.fill: parent
        
        // Layer 1: Waveform Visualization (bottom layer - respects SVG z-order)
        // Draws radial bars in the waveform element area
        Canvas {
            id: waveformCanvas
            anchors.fill: parent
            visible: isRecording
            
            // SVG z-order: background -> input_levels -> waveform -> mic/border
            // We render visualization in waveform area, let SVG handle the rest
            
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                
                if (!isRecording || audioSamples.length === 0) return
                
                // Calculate center and ring dimensions from waveform bounds
                var centerX = waveformBounds.x + waveformBounds.width / 2
                var centerY = waveformBounds.y + waveformBounds.height / 2
                var innerRadius = Math.min(waveformBounds.width, waveformBounds.height) * 0.35
                var outerRadius = Math.min(waveformBounds.width, waveformBounds.height) * 0.48
                
                ctx.save()
                ctx.translate(centerX, centerY)
                
                // Draw 36 radial bars
                var numBars = 36
                for (var i = 0; i < numBars; i++) {
                    var angle = (i / numBars) * 2 * Math.PI - (Math.PI / 2)
                    
                    // Get sample for this bar
                    var sampleIndex = Math.floor((i / numBars) * audioSamples.length)
                    var rawSample = Math.abs(audioSamples[sampleIndex] || 0)
                    
                    // Amplify sample for visualization (input is often very quiet)
                    var sample = Math.min(1.0, rawSample * 10)
                    
                    // Calculate bar length with minimum visible length
                    var maxLength = outerRadius - innerRadius - 4
                    var minLength = 5  // Minimum visible length
                    var barLength = minLength + (sample * maxLength * 0.8)
                    
                    // Calculate color
                    var r, g, b
                    if (sample < 0.5) {
                        r = Math.floor((0.2 + sample * 2 * 0.8) * 255)
                        g = Math.floor(0.8 * 255)
                        b = Math.floor(0.2 * 255)
                    } else {
                        r = Math.floor(1.0 * 255)
                        g = Math.floor((0.8 - (sample - 0.5) * 2 * 0.8) * 255)
                        b = Math.floor(0.2 * 255)
                    }
                    
                    // Draw bar
                    ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + ", 0.9)"
                    ctx.lineWidth = 3
                    ctx.beginPath()
                    ctx.moveTo(
                        Math.cos(angle) * innerRadius,
                        Math.sin(angle) * innerRadius
                    )
                    ctx.lineTo(
                        Math.cos(angle) * (innerRadius + barLength),
                        Math.sin(angle) * (innerRadius + barLength)
                    )
                    ctx.stroke()
                }
                
                ctx.restore()
            }
            
            // Animation loop - 60fps
            Timer {
                interval: 16  // ~60fps
                running: parent.visible && isRecording
                repeat: true
                onTriggered: parent.requestPaint()
            }
        }
        
        // Layer 2: Input Level Color Overlay (middle layer)
        // Positioned exactly over the input_levels element from SVG
        // Blocks out everything below it to show audio activity clearly
        Rectangle {
            id: inputLevelOverlay
            x: inputLevelBounds.x
            y: inputLevelBounds.y
            width: inputLevelBounds.width
            height: inputLevelBounds.height
            color: getStatusColor()
            opacity: isRecording ? 0.85 : 0.0

            // Match the rounded corners of the SVG element
            radius: Math.min(width, height) * 0.25
            
            Behavior on opacity {
                NumberAnimation { duration: 200 }
            }
            
            Behavior on color {
                ColorAnimation { duration: 150 }
            }
        }
        
        // Layer 3: SVG Base (top layer - respects SVG's natural z-order)
        Image {
            id: svgBase
            anchors.fill: parent
            source: svgBridge ? "file://" + svgBridge.svgPath : ""
            smooth: true
            antialiasing: true
            mipmap: true
        }
        
        // Layer 4: Mouse Interaction
        MouseArea {
            anchors.fill: parent
            
            property point pressPos: Qt.point(0, 0)
            property bool wasDragged: false
            property bool isDoubleClickSequence: false
            
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            
            // Check if point is in clickable area (inside active_area element)
            function isInClickableArea(x, y) {
                // Clickable if inside activeAreaBounds (as defined in SVG)
                return x >= activeAreaBounds.x &&
                       x <= activeAreaBounds.x + activeAreaBounds.width &&
                       y >= activeAreaBounds.y &&
                       y <= activeAreaBounds.y + activeAreaBounds.height
            }
            
            onPressed: (mouse) => {
                if (!isInClickableArea(mouse.x, mouse.y)) {
                    mouse.accepted = false
                    return
                }
                
                pressPos = Qt.point(mouse.x, mouse.y)
                wasDragged = false
                
                if (mouse.button === Qt.LeftButton && clickTimer.running) {
                    clickTimer.stop()
                    isDoubleClickSequence = true
                } else {
                    isDoubleClickSequence = false
                }
                
                if (mouse.button === Qt.RightButton) {
                    contextMenu.popup()
                } else if (mouse.button === Qt.MiddleButton) {
                    if (dialogBridge) dialogBridge.openClipboard()
                }
            }
            
            onPositionChanged: (mouse) => {
                if (!(mouse.buttons & Qt.LeftButton)) return
                
                var dx = mouse.x - pressPos.x
                var dy = mouse.y - pressPos.y
                var distance = Math.sqrt(dx * dx + dy * dy)
                
                if (distance > 5 && !wasDragged) {
                    wasDragged = true
                    root.startSystemMove()
                }
            }
            
            onReleased: (mouse) => {
                if (mouse.button !== Qt.LeftButton) return
                
                if (wasDragged) {
                    wasDragged = false
                    return
                }
                
                if (isDoubleClickSequence) {
                    isDoubleClickSequence = false
                } else {
                    clickTimer.start()
                }
            }
            
            onDoubleClicked: {
                clickTimer.stop()
                if (dialogBridge) dialogBridge.dismissDialog()
            }
            
            onWheel: (wheel) => {
                var delta = wheel.angleDelta.y
                var sizeChange = delta > 0 ? 20 : -20
                var newSize = Math.max(100, Math.min(500, root.width + sizeChange))
                root.width = newSize
                root.height = newSize
                if (dialogBridge) dialogBridge.saveWindowSize(newSize)
            }
            
            Timer {
                id: clickTimer
                interval: 250
                onTriggered: if (dialogBridge) dialogBridge.toggleRecording()
            }
        }
    }
    
    // Context Menu
    Menu {
        id: contextMenu
        
        MenuItem {
            text: isRecording ? "Stop Recording" : "Start Recording"
            onTriggered: if (dialogBridge) dialogBridge.toggleRecording()
        }
        
        MenuSeparator {}
        
        MenuItem {
            text: "Open Clipboard"
            onTriggered: if (dialogBridge) dialogBridge.openClipboard()
        }
        
        MenuItem {
            text: "Settings"
            onTriggered: if (dialogBridge) dialogBridge.openSettings()
        }
        
        MenuSeparator {}
        
        MenuItem {
            text: "Dismiss"
            onTriggered: if (dialogBridge) dialogBridge.dismissDialog()
        }
    }
    
    // Transcribing indicator
    Rectangle {
        anchors {
            bottom: parent.bottom
            bottomMargin: parent.height * 0.12
            horizontalCenter: parent.horizontalCenter
        }
        width: parent.width * 0.3
        height: 4
        radius: 2
        color: "#9b59b6"
        visible: isTranscribing
        opacity: 0.9
    }
    
    // Initialization
    Component.onCompleted: {
        console.log("RecordingDialogVisualizer: Window created")
        console.log("Input level bounds: " + inputLevelBounds)
        console.log("Waveform bounds: " + waveformBounds)
        console.log("Active area bounds: " + activeAreaBounds)
        
        // Restore saved size
        if (dialogBridge) {
            var savedSize = dialogBridge.getWindowSize()
            if (savedSize >= 100 && savedSize <= 500) {
                root.width = savedSize
                root.height = savedSize
            }
        }
    }
    
    onClosing: {
        console.log("RecordingDialogVisualizer: Window closing")
        if (dialogBridge) dialogBridge.dialogClosed()
    }
}
