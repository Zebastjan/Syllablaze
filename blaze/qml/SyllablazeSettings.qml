import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: "Syllablaze Settings"
    width: 900
    height: 600
    minimumWidth: 750
    minimumHeight: 500

    pageStack.initialPage: Kirigami.ScrollablePage {
        id: mainPage
        title: "Settings"

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // Left sidebar with category list
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 220
                color: Kirigami.Theme.backgroundColor
                border.color: Kirigami.Theme.separatorColor
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 0
                    spacing: 0

                    // Header
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 60
                        color: Kirigami.Theme.alternateBackgroundColor

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 2

                            QQC2.Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: "Syllablaze"
                                font.pointSize: 14
                                font.bold: true
                            }
                            QQC2.Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: "Version 0.5"
                                font.pointSize: 9
                                color: Kirigami.Theme.disabledTextColor
                            }
                        }
                    }

                    Kirigami.Separator {
                        Layout.fillWidth: true
                    }

                    // Category list
                    ListView {
                        id: categoryList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        currentIndex: 0
                        highlightFollowsCurrentItem: true
                        highlightMoveDuration: 0

                        model: ListModel {
                            ListElement {
                                name: "Models"
                                icon: "download"
                                page: "pages/ModelsPage.qml"
                            }
                            ListElement {
                                name: "Audio"
                                icon: "audio-input-microphone"
                                page: "pages/AudioPage.qml"
                            }
                            ListElement {
                                name: "Transcription"
                                icon: "document-edit"
                                page: "pages/TranscriptionPage.qml"
                            }
                            ListElement {
                                name: "Shortcuts"
                                icon: "configure-shortcuts"
                                page: "pages/ShortcutsPage.qml"
                            }
                            ListElement {
                                name: "About"
                                icon: "help-about"
                                page: "pages/AboutPage.qml"
                            }
                        }

                        delegate: QQC2.ItemDelegate {
                            width: ListView.view.width
                            height: 48
                            highlighted: ListView.isCurrentItem

                            contentItem: RowLayout {
                                spacing: Kirigami.Units.largeSpacing

                                Kirigami.Icon {
                                    source: model.icon
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                                    Layout.leftMargin: Kirigami.Units.largeSpacing
                                }

                                QQC2.Label {
                                    text: model.name
                                    Layout.fillWidth: true
                                    font.weight: ListView.isCurrentItem ? Font.DemiBold : Font.Normal
                                }
                            }

                            onClicked: {
                                categoryList.currentIndex = index
                                contentLoader.setSource(model.page)
                            }
                        }

                        highlight: Rectangle {
                            color: Kirigami.Theme.highlightColor
                            opacity: 0.3
                        }
                    }

                    Kirigami.Separator {
                        Layout.fillWidth: true
                    }

                    // Footer with system settings link
                    QQC2.ItemDelegate {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44

                        contentItem: RowLayout {
                            spacing: Kirigami.Units.largeSpacing

                            Kirigami.Icon {
                                source: "configure"
                                Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                Layout.leftMargin: Kirigami.Units.largeSpacing
                            }

                            QQC2.Label {
                                text: "System Settings"
                                Layout.fillWidth: true
                                font.pointSize: 9
                                color: Kirigami.Theme.disabledTextColor
                            }
                        }

                        onClicked: {
                            // TODO: Open KDE System Settings
                        }
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillHeight: true
            }

            // Right content area
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Kirigami.Theme.backgroundColor

                Loader {
                    id: contentLoader
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    source: "pages/ModelsPage.qml"
                }
            }
        }
    }
}
