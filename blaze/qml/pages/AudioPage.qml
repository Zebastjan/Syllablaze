import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

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
            Kirigami.FormData.label: "Input Device:"
            model: ["Default Microphone"]
            // TODO: Populate from Python audio manager
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: "Sample Rate:"
            model: ["16kHz - best for Whisper", "Default for device"]
            currentIndex: 0
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
