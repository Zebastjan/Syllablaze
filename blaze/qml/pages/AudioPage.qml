import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    Component.onCompleted: {
        // Load current settings
        var currentMode = settingsBridge.getSampleRateMode()
        if (currentMode === "whisper") {
            sampleRateCombo.currentIndex = 0
        } else {
            sampleRateCombo.currentIndex = 1
        }
    }

    // Page header
    Kirigami.Heading {
        text: "Audio Settings"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Configure audio input and recording settings"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Input device selection
    Kirigami.FormLayout {
        Layout.fillWidth: true

        QQC2.ComboBox {
            id: deviceCombo
            Kirigami.FormData.label: "Input Device:"
            model: settingsBridge.getAudioDevices()
            textRole: "name"
            valueRole: "index"

            onActivated: {
                var device = model[currentIndex]
                settingsBridge.setMicIndex(device.index)
            }
        }

        QQC2.ComboBox {
            id: sampleRateCombo
            Kirigami.FormData.label: "Sample Rate:"
            model: ["16kHz - best for Whisper", "Default for device"]
            currentIndex: 0

            onActivated: {
                if (currentIndex === 0) {
                    settingsBridge.setSampleRateMode("whisper")
                } else {
                    settingsBridge.setSampleRateMode("device")
                }
            }
        }
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        type: Kirigami.MessageType.Information
        text: "16kHz sample rate is optimized for Whisper and provides the best transcription accuracy."
        visible: true
    }

    Item {
        Layout.fillHeight: true
    }
}
