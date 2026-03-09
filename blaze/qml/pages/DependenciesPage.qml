import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: dependenciesPage
    spacing: Kirigami.Units.largeSpacing

    // Page header
    Kirigami.Heading {
        text: "Backend Dependencies"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Manage optional backend dependencies for different speech recognition engines"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Properties
    property var backends: []
    property string currentBackend: ""
    property string installStatusMessage: ""
    property int installProgress: 0
    property bool isInstalling: false

    Component.onCompleted: {
        console.log("[DependenciesPage] Component.onCompleted - initializing")
        refreshBackends()
        
        // Connect to signals
        settingsBridge.dependencyInstallProgress.connect(onDependencyInstallProgress)
        settingsBridge.dependencyInstallComplete.connect(onDependencyInstallComplete)
        settingsBridge.backendAvailabilityChanged.connect(onBackendAvailabilityChanged)
        
        console.log("[DependenciesPage] Initialization complete")
    }

    function refreshBackends() {
        console.log("[DependenciesPage] Refreshing backend list")
        try {
            backends = settingsBridge.getAllBackendsWithStatus()
            console.log("[DependenciesPage] Loaded", backends.length, "backends")
        } catch (e) {
            console.log("[DependenciesPage] Error loading backends:", e.toString())
            backends = []
        }
    }

    function onDependencyInstallProgress(backend, message, progress) {
        console.log("[DependenciesPage] Install progress:", backend, message, progress)
        if (backend === currentBackend) {
            installStatusMessage = message
            installProgress = progress
        }
    }

    function onDependencyInstallComplete(backend, success) {
        console.log("[DependenciesPage] Install complete:", backend, success)
        isInstalling = false
        if (success) {
            installStatusMessage = "Installation successful!"
            refreshBackends()
            showMessage(backend + " backend installed successfully!", Kirigami.MessageType.Positive)
        } else {
            installStatusMessage = "Installation failed. Please check your internet connection."
            showError("Failed to install " + backend + " backend")
        }
    }

    function onBackendAvailabilityChanged(backend, available) {
        console.log("[DependenciesPage] Backend availability changed:", backend, available)
        refreshBackends()
    }

    function showError(text) {
        inlineMessage.text = text
        inlineMessage.type = Kirigami.MessageType.Error
        inlineMessage.visible = true
    }

    function showMessage(text, type) {
        inlineMessage.text = text
        inlineMessage.type = type || Kirigami.MessageType.Information
        inlineMessage.visible = true
    }

    // Inline messages
    Kirigami.InlineMessage {
        id: inlineMessage
        Layout.fillWidth: true
        visible: false
        showCloseButton: true
    }

    // Backend list
    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true

        ListView {
            model: backends
            spacing: Kirigami.Units.smallSpacing

            delegate: Kirigami.Card {
                width: ListView.view.width

                contentItem: RowLayout {
                    spacing: Kirigami.Units.largeSpacing

                    // Backend info
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: Kirigami.Units.smallSpacing

                        RowLayout {
                            spacing: Kirigami.Units.smallSpacing
                            Layout.alignment: Qt.AlignVCenter

                            // Backend name
                            QQC2.Label {
                                text: modelData.name.charAt(0).toUpperCase() + modelData.name.slice(1)
                                font.bold: true
                                font.pointSize: 11
                            }

                            // Status badge
                            Rectangle {
                                color: modelData.available 
                                    ? Kirigami.Theme.positiveBackgroundColor 
                                    : Kirigami.Theme.neutralBackgroundColor
                                radius: 3
                                Layout.preferredWidth: statusLabel.implicitWidth + 10
                                Layout.preferredHeight: 20
                                
                                QQC2.Label {
                                    id: statusLabel
                                    anchors.centerIn: parent
                                    text: modelData.available ? "✓ Available" : "Not Installed"
                                    font.pointSize: 8
                                    font.bold: true
                                    color: modelData.available 
                                        ? Kirigami.Theme.positiveTextColor 
                                        : Kirigami.Theme.neutralTextColor
                                }
                            }
                        }

                        // Description
                        QQC2.Label {
                            text: modelData.description || ""
                            font.pointSize: 9
                            color: Kirigami.Theme.textColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        // Packages info
                        QQC2.Label {
                            visible: !modelData.available
                            text: "Required: " + (modelData.packages ? modelData.packages.join(", ") : "")
                            font.pointSize: 8
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            font.family: "monospace"
                        }

                        // Models count
                        QQC2.Label {
                            text: modelData.models_available + " models available"
                            font.pointSize: 8
                            color: Kirigami.Theme.disabledTextColor
                        }

                        // Size estimate
                        QQC2.Label {
                            visible: !modelData.available
                            text: "Download size: " + (modelData.size_estimate || "Unknown")
                            font.pointSize: 8
                            color: Kirigami.Theme.disabledTextColor
                        }
                    }

                    // Spacer
                    Item { Layout.fillWidth: true }

                    // Action buttons
                    RowLayout {
                        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                        spacing: Kirigami.Units.smallSpacing

                        // Install button (only for unavailable backends)
                        QQC2.Button {
                            visible: !modelData.available && !isInstalling
                            text: "Install"
                            icon.name: "download"
                            onClicked: {
                                currentBackend = modelData.name
                                isInstalling = true
                                installProgress = 0
                                installStatusMessage = "Starting installation..."
                                settingsBridge.installBackendDependencies(modelData.name)
                            }
                        }

                        // Already installed indicator
                        Kirigami.Icon {
                            visible: modelData.available
                            source: "emblem-checked"
                            Layout.preferredWidth: Kirigami.Units.iconSizes.small
                            Layout.preferredHeight: Kirigami.Units.iconSizes.small
                            color: Kirigami.Theme.positiveTextColor
                        }

                        QQC2.Label {
                            visible: modelData.available
                            text: "Installed"
                            color: Kirigami.Theme.positiveTextColor
                        }
                    }
                }
            }
        }
    }

    // Installation progress section
    Kirigami.Card {
        Layout.fillWidth: true
        visible: isInstalling

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Kirigami.Heading {
                    text: "Installing " + currentBackend + "..."
                    level: 4
                }
                
                Item { Layout.fillWidth: true }
                
                QQC2.BusyIndicator {
                    running: true
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                }
            }

            QQC2.ProgressBar {
                Layout.fillWidth: true
                from: 0
                to: 100
                value: installProgress
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: installStatusMessage
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
            }

            QQC2.Button {
                text: "Cancel"
                onClicked: {
                    // Note: pip install can't be easily cancelled, 
                    // but we can close the progress view
                    isInstalling = false
                }
            }
        }
    }

    // Info card
    Kirigami.Card {
        Layout.fillWidth: true
        visible: !isInstalling

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                text: "About Backend Dependencies"
                level: 4
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Syllablaze supports multiple speech recognition backends. The Whisper backend is included by default. Optional backends like Liquid require additional Python packages to be installed."
                wrapMode: Text.WordWrap
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Installing a backend will download the required Python packages (~3-7GB depending on the backend). You'll need an internet connection and sufficient disk space."
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
            }
        }
    }
}
