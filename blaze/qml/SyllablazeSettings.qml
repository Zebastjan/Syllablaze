import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: "Syllablaze Settings"
    visible: false  // Start hidden, show() will make it visible

    // Scale based on 4K baseline (3840×2160 → 900×616)
    Component.onCompleted: {
        var screenWidth = 1920  // Default fallback
        var screenHeight = 1080
        var logicalWidth = screenWidth
        var logicalHeight = screenHeight
        var devicePixelRatio = 1.0

        var screen = Qt.application.screens && Qt.application.screens[0]
        if (screen && screen.width && screen.height) {
            // Get logical screen dimensions
            if (screen.availableGeometry && screen.availableGeometry.width) {
                logicalWidth = screen.availableGeometry.width
                logicalHeight = screen.availableGeometry.height
            } else if (screen.desktopAvailableWidth && screen.desktopAvailableHeight) {
                logicalWidth = screen.desktopAvailableWidth
                logicalHeight = screen.desktopAvailableHeight
            } else {
                logicalWidth = screen.width
                logicalHeight = screen.height
            }

            // Get device pixel ratio to convert logical → physical resolution
            if (screen.devicePixelRatio) {
                devicePixelRatio = screen.devicePixelRatio
            }

            // Calculate PHYSICAL screen resolution (accounting for display scaling)
            screenWidth = Math.round(logicalWidth * devicePixelRatio)
            screenHeight = Math.round(logicalHeight * devicePixelRatio)

            console.log("Display scaling detected:",
                        "Logical:", logicalWidth, "×", logicalHeight,
                        "DPR:", devicePixelRatio.toFixed(2),
                        "Physical:", screenWidth, "×", screenHeight)
        } else {
            console.log("No screen info available, using default 1920×1080")
        }

        // Baseline: 900×616 looks perfect on 4K (3840×2160)
        var baseWidth = 900
        var baseHeight = 616
        var baseScreenWidth = 3840
        var baseScreenHeight = 2160

        // Scale proportionally to PHYSICAL screen resolution
        var scaleFactor = Math.min(screenWidth / baseScreenWidth, screenHeight / baseScreenHeight)
        var targetWidth = Math.round(baseWidth * scaleFactor)
        var targetHeight = Math.round(baseHeight * scaleFactor)

        // Clamp to reasonable bounds
        width = Math.max(600, Math.min(1200, targetWidth))
        height = Math.max(400, Math.min(900, targetHeight))

        console.log("Window sizing: Physical screen", screenWidth, "×", screenHeight,
                    "→ Scale factor:", scaleFactor.toFixed(2),
                    "→ Window:", width, "×", height)
    }

    // Allow resizing within reasonable bounds
    minimumWidth: 600
    minimumHeight: 400
    maximumWidth: 1200
    maximumHeight: 900

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
                border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.2)
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
                                name: "User Interface"
                                icon: "window"
                                page: "pages/UIPage.qml"
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
                            console.log("Sidebar System Settings button clicked")
                            try {
                                actionsBridge.openSystemSettings()
                                console.log("openSystemSettings() called successfully")
                            } catch (error) {
                                console.error("Error calling openSystemSettings():", error)
                            }
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
