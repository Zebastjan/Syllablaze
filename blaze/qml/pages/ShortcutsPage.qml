import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    // Page header
    Kirigami.Heading {
        text: "Keyboard Shortcuts"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Global keyboard shortcuts for Syllablaze"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Current shortcut display
    Kirigami.FormLayout {
        Layout.fillWidth: true

        RowLayout {
            Kirigami.FormData.label: "Toggle Recording:"
            spacing: Kirigami.Units.smallSpacing

            Rectangle {
                Layout.preferredWidth: 120
                Layout.preferredHeight: 32
                color: Kirigami.Theme.alternateBackgroundColor
                border.color: Kirigami.Theme.highlightColor
                border.width: 2
                radius: 4

                QQC2.Label {
                    anchors.centerIn: parent
                    text: "Alt+Space"
                    font.bold: true
                }
            }

            QQC2.Button {
                text: "Configure in System Settings"
                icon.name: "configure-shortcuts"
                onClicked: {
                    // TODO: Open systemsettings kcm_keys
                }
            }
        }
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.largeSpacing
        type: Kirigami.MessageType.Information
        text: "Shortcuts are managed by KDE System Settings for full Wayland support and native desktop integration. Changes take effect immediately."
        visible: true
    }

    // Info card
    Kirigami.Card {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.largeSpacing

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                spacing: Kirigami.Units.largeSpacing

                Kirigami.Icon {
                    source: "help-about"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true

                    Kirigami.Heading {
                        text: "Native KDE Integration"
                        level: 3
                    }

                    QQC2.Label {
                        Layout.fillWidth: true
                        text: "Syllablaze uses KDE's kglobalaccel service for global shortcuts. This provides:\n\n• Full Wayland compatibility\n• Customization through System Settings\n• Conflict detection with other apps\n• Persistent shortcuts across sessions"
                        wrapMode: Text.WordWrap
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }
        }
    }

    Item {
        Layout.fillHeight: true
    }
}
