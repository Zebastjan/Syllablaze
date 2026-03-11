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
    property string uninstallStatusMessage: ""
    property int installProgress: 0
    property int uninstallProgress: 0
    property bool isInstalling: false
    property bool isUninstalling: false

    Component.onCompleted: {
        console.log("[DependenciesPage] Component.onCompleted - initializing")
        refreshBackends()

        // Connect to install signals
        settingsBridge.dependencyInstallProgress.connect(onDependencyInstallProgress)
        settingsBridge.dependencyInstallComplete.connect(onDependencyInstallComplete)

        // Connect to uninstall signals
        settingsBridge.dependencyUninstallProgress.connect(onDependencyUninstallProgress)
        settingsBridge.dependencyUninstallComplete.connect(onDependencyUninstallComplete)

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

    function getStatusText(backend) {
        if (backend.available) {
            return "✓ Ready"
        } else if (backend.python_deps_installed && !backend.binary_installed) {
            return "⚠ Setup Incomplete"
        } else {
            return "Not Installed"
        }
    }

    function getStatusColor(backend) {
        if (backend.available) {
            return Kirigami.Theme.positiveBackgroundColor
        } else if (backend.python_deps_installed) {
            return Kirigami.Theme.neutralBackgroundColor
        } else {
            return Kirigami.Theme.negativeBackgroundColor
        }
    }

    function getStatusTextColor(backend) {
        if (backend.available) {
            return Kirigami.Theme.positiveTextColor
        } else if (backend.python_deps_installed) {
            return Kirigami.Theme.neutralTextColor
        } else {
            return Kirigami.Theme.negativeTextColor
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

            // Check if it's a partial install (like Qwen)
            var status = settingsBridge.getBackendDetailedStatus(backend)
            if (status.python_deps_installed && !status.available && status.missing_binary) {
                showMessage(
                    backend + " Python dependencies installed. Manual step required: Install " + status.missing_binary,
                    Kirigami.MessageType.Warning
                )
            } else {
                showMessage(backend + " backend installed successfully!", Kirigami.MessageType.Positive)
            }
        } else {
            installStatusMessage = "Installation failed. Please check your internet connection."
            showError("Failed to install " + backend + " backend")
        }
    }

    function onDependencyUninstallProgress(backend, message, progress) {
        console.log("[DependenciesPage] Uninstall progress:", backend, message, progress)
        if (backend === currentBackend) {
            uninstallStatusMessage = message
            uninstallProgress = progress
        }
    }

    function onDependencyUninstallComplete(backend, result) {
        console.log("[DependenciesPage] Uninstall complete:", backend, JSON.stringify(result))
        isUninstalling = false

        if (result.success) {
            refreshBackends()

            // Show appropriate message based on what was done
            var message = backend + " uninstalled"
            if (result.uninstalled.length > 0) {
                message += "\nRemoved: " + result.uninstalled.join(", ")
            }

            if (result.skipped.length > 0) {
                message += "\n\n⚠ Kept shared packages:\n" + result.skipped.join(", ")
                message += "\n\n(These are still needed by other backends)"
                showMessage(message, Kirigami.MessageType.Warning)
            } else {
                showMessage(message, Kirigami.MessageType.Positive)
            }
        } else {
            var errorMsg = "Failed to uninstall " + backend
            if (result.warnings && result.warnings.length > 0) {
                errorMsg += "\n" + result.warnings.join("\n")
            }
            showError(errorMsg)
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

                            // Status badge (3 states: green/orange/red)
                            Rectangle {
                                color: getStatusColor(modelData)
                                radius: 3
                                Layout.preferredWidth: statusLabel.implicitWidth + 10
                                Layout.preferredHeight: 20

                                QQC2.Label {
                                    id: statusLabel
                                    anchors.centerIn: parent
                                    text: getStatusText(modelData)
                                    font.pointSize: 8
                                    font.bold: true
                                    color: getStatusTextColor(modelData)
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

                        // Special message for Qwen if partially installed
                        QQC2.Label {
                            visible: modelData.name === "qwen" && modelData.python_deps_installed && !modelData.available
                            text: "⚠ Manual step required: Compile and install " + (modelData.missing_binary || "llama-mtmd-cli")
                            font.pointSize: 9
                            color: Kirigami.Theme.neutralTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            font.bold: true
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

                        // Install button (for unavailable backends)
                        QQC2.Button {
                            visible: !modelData.available && !isInstalling
                            text: {
                                if (modelData.name === "qwen" && modelData.python_deps_installed) {
                                    return "Auto Install Binary"
                                }
                                return modelData.python_deps_installed ? "View Instructions" : "Install"
                            }
                            icon.name: {
                                if (modelData.name === "qwen" && modelData.python_deps_installed) {
                                    return "run-build"
                                }
                                return modelData.python_deps_installed ? "help-about" : "download"
                            }
                            onClicked: {
                                currentBackend = modelData.name

                                // If Qwen and partial install, auto-install binary
                                if (modelData.name === "qwen" && modelData.python_deps_installed) {
                                    isInstalling = true
                                    installProgress = 0
                                    installStatusMessage = "Building llama-mtmd-cli (5-15 minutes)..."
                                    settingsBridge.installQwenBinary(modelData.name)
                                } else {
                                    isInstalling = true
                                    installProgress = 0
                                    installStatusMessage = "Starting installation..."
                                    settingsBridge.installBackendDependencies(modelData.name)
                                }
                            }
                        }

                        // Manual instructions button (for Qwen partial installs)
                        QQC2.Button {
                            visible: !modelData.available && !isInstalling && modelData.name === "qwen" && modelData.python_deps_installed
                            text: "Manual Instructions"
                            icon.name: "help-about"
                            onClicked: {
                                qwenInstructionsDialog.open()
                            }
                        }

                        // Uninstall button (for backends with Python deps installed)
                        QQC2.Button {
                            visible: modelData.python_deps_installed && !isUninstalling
                            text: "Uninstall"
                            icon.name: "delete"
                            onClicked: {
                                currentBackend = modelData.name
                                uninstallConfirmDialog.backendName = modelData.name
                                uninstallConfirmDialog.open()
                            }
                        }

                        // Status icon (for fully available backends)
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

    // Uninstallation progress section
    Kirigami.Card {
        Layout.fillWidth: true
        visible: isUninstalling

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Kirigami.Heading {
                    text: "Uninstalling " + currentBackend + "..."
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
                value: uninstallProgress
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: uninstallStatusMessage
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
            }
        }
    }

    // Info card
    Kirigami.Card {
        Layout.fillWidth: true
        visible: !isInstalling && !isUninstalling

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                text: "About Backend Dependencies"
                level: 4
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Syllablaze supports multiple speech recognition backends. The Whisper backend is included by default. Optional backends like Liquid and Granite require additional Python packages to be installed."
                wrapMode: Text.WordWrap
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Installing a backend will download the required Python packages (~3-7GB depending on the backend). You'll need an internet connection and sufficient disk space."
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "⚠ Shared Dependencies: Some packages (like torchaudio) are used by multiple backends. Uninstalling a backend will keep shared packages if other backends still need them."
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.neutralTextColor
                font.bold: true
            }
        }
    }

    // Uninstall confirmation dialog
    Kirigami.PromptDialog {
        id: uninstallConfirmDialog
        property string backendName: ""

        title: "Uninstall " + backendName + "?"
        subtitle: "This will remove Python dependencies for the " + backendName + " backend.\n\nShared dependencies (used by other backends) will be kept safe."

        standardButtons: QQC2.Dialog.Ok | QQC2.Dialog.Cancel

        onAccepted: {
            isUninstalling = true
            uninstallProgress = 0
            uninstallStatusMessage = "Analyzing dependencies..."
            settingsBridge.uninstallBackendDependencies(backendName)
        }
    }

    // Qwen instructions dialog
    Kirigami.PromptDialog {
        id: qwenInstructionsDialog

        title: "Qwen Setup Instructions (Manual/Advanced)"
        subtitle: "Use 'Auto Install Binary' for automated setup, or follow these manual steps:"

        standardButtons: QQC2.Dialog.Close

        customFooterActions: [
            Kirigami.Action {
                text: "Copy Install Commands"
                icon.name: "edit-copy"
                onTriggered: {
                    var commands = "cd ~ && git clone https://github.com/ggml-org/llama.cpp.git\n" +
                                 "cd llama.cpp && mkdir -p build && cd build\n" +
                                 "cmake .. -DGGML_CUDA=ON -DLLAMA_BUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release\n" +
                                 "cmake --build . --target llama-mtmd-cli -j$(nproc)\n" +
                                 "sudo cp bin/llama-mtmd-cli /usr/local/bin/"
                    // Copy to clipboard (if available)
                    console.log("Commands to copy:", commands)
                }
            }
        ]

        contentItem: QQC2.ScrollView {
            implicitWidth: 500
            implicitHeight: 300

            QQC2.Label {
                text: "1. Clone llama.cpp:\n   cd ~ && git clone https://github.com/ggml-org/llama.cpp.git\n\n" +
                      "2. Configure with CMake:\n   cd llama.cpp && mkdir -p build && cd build\n" +
                      "   cmake .. -DGGML_CUDA=ON -DLLAMA_BUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release\n\n" +
                      "3. Compile multimodal CLI:\n   cmake --build . --target llama-mtmd-cli -j$(nproc)\n\n" +
                      "4. Install binary:\n   sudo cp bin/llama-mtmd-cli /usr/local/bin/\n   " +
                      "# OR: mkdir -p ~/.local/bin && cp bin/llama-mtmd-cli ~/.local/bin/\n\n" +
                      "5. Verify installation:\n   llama-mtmd-cli --help\n\n" +
                      "After installation, Qwen will show as \"✓ Ready\" and you can download Qwen models.\n\n" +
                      "Build docs: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md"
                wrapMode: Text.WordWrap
                font.family: "monospace"
            }
        }
    }
}
