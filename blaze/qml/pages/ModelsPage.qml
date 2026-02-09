import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    // Page header
    Kirigami.Heading {
        text: "Whisper Models"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Download and manage Whisper speech recognition models"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Models list placeholder
    Kirigami.PlaceholderMessage {
        Layout.fillWidth: true
        Layout.fillHeight: true
        icon.name: "download"
        text: "Model Management"
        explanation: "Download Whisper models for speech recognition.\n\nThis will be integrated with the Python model manager."
    }

    Item {
        Layout.fillHeight: true
    }
}
