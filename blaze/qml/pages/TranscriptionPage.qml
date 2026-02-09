import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    // Page header
    Kirigami.Heading {
        text: "Transcription Settings"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Configure language and transcription options"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Settings form
    Kirigami.FormLayout {
        Layout.fillWidth: true

        QQC2.ComboBox {
            Kirigami.FormData.label: "Language:"
            model: ["Auto-detect", "English", "Spanish", "French", "German", "Italian"]
            currentIndex: 0
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: "Compute Type:"
            model: ["float32", "float16", "int8"]
            currentIndex: 0
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: "Device:"
            model: ["CPU", "CUDA (GPU)"]
            currentIndex: 0
        }

        QQC2.SpinBox {
            Kirigami.FormData.label: "Beam Size:"
            from: 1
            to: 10
            value: 5
        }

        QQC2.CheckBox {
            Kirigami.FormData.label: "Voice Activity Detection:"
            text: "Use VAD filter to remove silence"
            checked: true
        }

        QQC2.CheckBox {
            Kirigami.FormData.label: "Word Timestamps:"
            text: "Generate word-level timestamps"
            checked: false
        }
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        type: Kirigami.MessageType.Information
        text: "VAD (Voice Activity Detection) helps improve accuracy by filtering out silence and background noise."
        visible: true
    }

    Item {
        Layout.fillHeight: true
    }
}
