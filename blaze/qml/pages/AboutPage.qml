import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    // Page header
    Kirigami.Heading {
        text: "About Syllablaze"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Speech-to-text transcription for KDE Plasma"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // App info card
    Kirigami.Card {
        Layout.fillWidth: true

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                spacing: Kirigami.Units.largeSpacing

                Kirigami.Icon {
                    source: "syllablaze"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                    Layout.preferredHeight: Kirigami.Units.iconSizes.huge
                    fallback: "media-record"
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true

                    Kirigami.Heading {
                        text: APP_NAME
                        level: 1
                    }

                    QQC2.Label {
                        text: "Version " + APP_VERSION
                        color: Kirigami.Theme.disabledTextColor
                    }

                    QQC2.Label {
                        Layout.fillWidth: true
                        Layout.topMargin: Kirigami.Units.smallSpacing
                        text: "A PyQt6 system tray application for real-time speech-to-text transcription using OpenAI's Whisper (via faster-whisper)."
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    // Features card
    Kirigami.Card {
        Layout.fillWidth: true
        Layout.maximumWidth: parent.width - Kirigami.Units.largeSpacing * 2

        header: Kirigami.Heading {
            text: "Features"
            level: 3
            leftPadding: Kirigami.Units.largeSpacing
            topPadding: Kirigami.Units.largeSpacing
        }

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            Layout.fillWidth: true

            Repeater {
                model: [
                    "Real-time audio recording and transcription",
                    "Multiple Whisper model support",
                    "GPU acceleration (CUDA)",
                    "Native KDE global shortcuts",
                    "Automatic clipboard integration",
                    "Voice Activity Detection (VAD)",
                    "Multi-language support"
                ]

                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Icon {
                        source: "emblem-checked"
                        Layout.preferredWidth: Kirigami.Units.iconSizes.small
                        Layout.preferredHeight: Kirigami.Units.iconSizes.small
                        color: Kirigami.Theme.positiveTextColor
                    }

                    QQC2.Label {
                        text: modelData
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    // Links
    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.largeSpacing

        QQC2.Button {
            text: "GitHub Repository"
            icon.name: "internet-services"
            onClicked: {
                actionsBridge.openUrl(GITHUB_REPO_URL)
            }
        }

        QQC2.Button {
            text: "Report Issue"
            icon.name: "tools-report-bug"
            onClicked: {
                actionsBridge.openUrl(GITHUB_REPO_URL + "/issues")
            }
        }
    }

    Item {
        Layout.fillHeight: true
    }
}
