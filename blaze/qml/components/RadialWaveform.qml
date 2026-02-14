import QtQuick 2.15
import QtQuick.Shapes 1.15

Item {
    id: root

    // Properties
    property real volume: 0.0
    property bool isRecording: false
    property var audioSamples: []
    property real baseRadius: 60
    property real maxAmplitude: 40

    width: 300
    height: 300

    // Repeater to create waveform segments
    Repeater {
        model: isRecording && audioSamples.length > 0 ? audioSamples.length : 0

        Rectangle {
            id: segment

            property real angle: (index / audioSamples.length) * Math.PI * 2
            property real sampleValue: audioSamples[index] !== undefined ? Math.abs(audioSamples[index]) : 0
            property real amplitude: maxAmplitude * sampleValue
            property real radius: baseRadius + amplitude

            // Position at the angle
            x: root.width / 2 + Math.cos(angle) * radius - width / 2
            y: root.height / 2 + Math.sin(angle) * radius - height / 2

            width: 3
            height: 3
            radius: 1.5

            // Color based on volume
            color: {
                if (root.volume < 0.6) {
                    return Qt.rgba(0.2, 0.8, 0.2, 0.6 + root.volume * 0.4)
                } else if (root.volume < 0.85) {
                    return Qt.rgba(1.0, 0.7, 0.0, 0.7 + root.volume * 0.3)
                } else {
                    return Qt.rgba(1.0, 0.2, 0.0, 0.8 + root.volume * 0.2)
                }
            }

            Behavior on x {
                NumberAnimation { duration: 50; easing.type: Easing.OutQuad }
            }
            Behavior on y {
                NumberAnimation { duration: 50; easing.type: Easing.OutQuad }
            }
        }
    }
}
