import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: modelsPage
    spacing: Kirigami.Units.largeSpacing

    // Page header
    Kirigami.Heading {
        text: "Speech Recognition Models"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Download and manage speech-to-text models for different languages and hardware"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Hardware Info + Language Selection Card
    Kirigami.Card {
        Layout.fillWidth: true
        visible: hardwareInfo.total_ram_gb !== undefined
        
        contentItem: RowLayout {
            spacing: Kirigami.Units.largeSpacing
            
            // Left column: Hardware Info
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                
                Kirigami.Heading {
                    text: "Your System"
                    level: 3
                }
                
                QQC2.Label {
                    text: "💻 RAM: " + (hardwareInfo.available_ram_gb || "?") + " GB available / " + (hardwareInfo.total_ram_gb || "?") + " GB total"
                }
                
                QQC2.Label {
                    visible: hardwareInfo.gpu_available && hardwareInfo.primary_gpu_name
                    text: "🎮 GPU: " + (hardwareInfo.primary_gpu_name || "") + (hardwareInfo.primary_gpu_vram_gb > 0 ? " (" + hardwareInfo.primary_gpu_vram_gb + "GB VRAM)" : "")
                    color: Kirigami.Theme.positiveTextColor
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                
                QQC2.Label {
                    visible: !hardwareInfo.gpu_available
                    text: "🎮 GPU: None detected (CPU only)"
                    color: Kirigami.Theme.disabledTextColor
                }
                
                QQC2.Label {
                    visible: recommendedModel.id !== undefined
                    text: "⭐ Recommended: " + (recommendedModel.name || "")
                    font.bold: true
                    color: Kirigami.Theme.positiveTextColor
                }
            }
            
            // Right column: Language Selection
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                Layout.minimumWidth: 200
                
                Kirigami.Heading {
                    text: "Language Preferences"
                    level: 3
                }
                
                QQC2.CheckBox {
                    text: "Multilingual models (all languages)"
                    checked: multilingualMode
                    onCheckedChanged: {
                        multilingualMode = checked
                        settingsBridge.setLanguageMultilingual(checked)
                    }
                }
                
                QQC2.Label {
                    text: "Or select specific language:"
                    font.pointSize: 9
                    color: Kirigami.Theme.disabledTextColor
                    enabled: !multilingualMode
                }
                
                QQC2.ComboBox {
                    enabled: !multilingualMode
                    model: availableLanguages
                    textRole: "name"
                    valueRole: "code"
                    currentIndex: {
                        for (var i = 0; i < availableLanguages.length; i++) {
                            if (availableLanguages[i].code === specificLanguage) {
                                return i
                            }
                        }
                        return 0
                    }
                    onActivated: {
                        specificLanguage = model.get(currentIndex).code
                        settingsBridge.setLanguageSpecific(specificLanguage)
                    }
                    Layout.fillWidth: true
                }
            }
        }
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Backend filter tabs
    QQC2.TabBar {
        id: backendTabBar
        Layout.fillWidth: true
        
        QQC2.TabButton {
            text: "All"
            onClicked: {
                currentBackendFilter = "all"
                refreshModels()
            }
        }
        QQC2.TabButton {
            text: "Whisper"
            onClicked: {
                currentBackendFilter = "whisper"
                refreshModels()
            }
        }
        QQC2.TabButton {
            text: "Liquid"
            onClicked: {
                currentBackendFilter = "liquid"
                refreshModels()
            }
        }
        QQC2.TabButton {
            text: "Granite"
            onClicked: {
                currentBackendFilter = "granite"
                refreshModels()
            }
        }
        QQC2.TabButton {
            text: "Qwen"
            onClicked: {
                currentBackendFilter = "qwen"
                refreshModels()
            }
        }
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Properties
    property var models: []
    property var downloadingModels: ({})
    property var hardwareInfo: ({})
    property var recommendedModel: ({})
    property bool multilingualMode: false
    property string specificLanguage: ""
    property var availableLanguages: []
    property string currentBackendFilter: "all"

    // Debug output when models change
    onModelsChanged: {
        console.log("[ModelsPage] models changed, count:", models.length)
        if (models.length > 0) {
            console.log("[ModelsPage] First model id:", models[0].id, "name:", models[0].name)
        }
    }

    Component.onCompleted: {
        console.log("[ModelsPage] Component.onCompleted - initializing")
        
        // Load language preferences
        try {
            availableLanguages = settingsBridge.getAvailableLanguages()
            specificLanguage = settingsBridge.getLanguageSpecific()
            multilingualMode = settingsBridge.getLanguageMultilingual()
            console.log("[ModelsPage] Loaded language preferences:", availableLanguages.length, "languages available")
        } catch (e) {
            console.log("[ModelsPage] Error loading language preferences:", e.toString())
            availableLanguages = [{"code": "en", "name": "English"}]
            specificLanguage = "en"
            multilingualMode = true
        }
        
        // Load initial data
        refreshModels()
        refreshHardwareInfo()
        
        // Connect signals
        settingsBridge.modelDownloadProgress.connect(onDownloadProgress)
        settingsBridge.modelDownloadComplete.connect(onDownloadComplete)
        settingsBridge.modelDownloadError.connect(onDownloadError)
        settingsBridge.settingChanged.connect(onSettingChanged)
        settingsBridge.dependencyInstallProgress.connect(onDependencyInstallProgress)
        settingsBridge.dependencyInstallComplete.connect(onDependencyInstallComplete)
        
        console.log("[ModelsPage] Initialization complete")
    }
    
    function onDependencyInstallProgress(backend, message, progress) {
        console.log("[ModelsPage] Dependency install progress:", backend, message, progress)
        if (dependencyInstallDialog) {
            dependencyInstallDialog.statusMessage = message
            dependencyInstallDialog.progress = progress
        }
    }
    
    function onDependencyInstallComplete(backend, success) {
        console.log("[ModelsPage] Dependency install complete:", backend, success)
        if (dependencyInstallDialog) {
            dependencyInstallDialog.installing = false
            if (success) {
                dependencyInstallDialog.close()
                showMessage(backend + " backend installed successfully! You can now download models.", Kirigami.MessageType.Positive)
                // Refresh the model list to show new availability
                refreshModels()
            } else {
                dependencyInstallDialog.statusMessage = "Installation failed. Please check your internet connection and try again."
            }
        }
    }

    function refreshModels() {
        console.log("[ModelsPage] refreshModels called")
        
        var languageFilter = multilingualMode ? "all" : (specificLanguage || "en")
        console.log("[ModelsPage] languageFilter:", languageFilter, "backendFilter:", currentBackendFilter)
        
        try {
            var result = settingsBridge.getAvailableModels(languageFilter, currentBackendFilter)
            console.log("[ModelsPage] getAvailableModels returned type:", typeof result)
            console.log("[ModelsPage] Result:", JSON.stringify(result))
            
            // Handle both array and object-with-length cases
            // PyQt6 might return QVariant which QML sees as object
            if (result && (Array.isArray(result) || (result.length !== undefined && typeof result === 'object'))) {
                var count = result.length || 0
                console.log("[ModelsPage] Got", count, "models")
                if (count > 0) {
                    // Convert to proper array if needed
                    var modelArray = []
                    for (var i = 0; i < count; i++) {
                        modelArray.push(result[i])
                    }
                    models = modelArray
                } else {
                    models = []
                }
            } else {
                console.log("[ModelsPage] ERROR: Expected array, got:", typeof result, "value:", result)
                models = []
                showError("Failed to load models - invalid response type: " + typeof result)
            }
        } catch (e) {
            console.log("[ModelsPage] ERROR in refreshModels:", e.toString())
            models = []
            showError("Error loading models: " + e.toString())
        }
    }

    function refreshHardwareInfo() {
        console.log("[ModelsPage] refreshHardwareInfo called")
        try {
            hardwareInfo = settingsBridge.getHardwareInfo()
            recommendedModel = settingsBridge.getRecommendedModel()
            console.log("[ModelsPage] Hardware info loaded:", JSON.stringify(hardwareInfo))
        } catch (e) {
            console.log("[ModelsPage] Error loading hardware info:", e.toString())
        }
    }

    function onSettingChanged(key, value) {
        if (key === "language_mode_changed") {
            console.log("[ModelsPage] Language mode changed, refreshing models")
            refreshModels()
        }
    }

    function onDownloadProgress(modelName, progress) {
        downloadingModels[modelName] = progress
        downloadingModelsChanged()
    }

    function onDownloadComplete(modelName) {
        console.log("[ModelsPage] Download complete:", modelName)
        delete downloadingModels[modelName]
        downloadingModelsChanged()
        refreshModels()
        showMessage("Download complete: " + modelName, Kirigami.MessageType.Positive)
    }

    function onDownloadError(modelName, error) {
        console.log("[ModelsPage] Download error:", modelName, error)
        delete downloadingModels[modelName]
        downloadingModelsChanged()
        
        // Check if this is a backend availability error
        if (error.indexOf("Backend") !== -1 && error.indexOf("not available") !== -1) {
            var backend = settingsBridge.getBackendForModel(modelName)
            if (backend) {
                dependencyInstallDialog.modelId = modelName
                dependencyInstallDialog.backend = backend
                dependencyInstallDialog.open()
                return
            }
        }
        
        showError("Download failed: " + error)
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

    Kirigami.InlineMessage {
        id: noModelsMessage
        Layout.fillWidth: true
        visible: models.length === 0 && !inlineMessage.visible
        type: Kirigami.MessageType.Warning
        text: "No models found. This may indicate an issue with the model registry. Try restarting the application."
        showCloseButton: false
    }

    // Debug counter
    QQC2.Label {
        Layout.fillWidth: true
        text: "Models loaded: " + models.length
        color: Kirigami.Theme.disabledTextColor
        font.pointSize: 9
        visible: models.length > 0
    }

    // Model list
    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: models.length > 0

        ListView {
            model: modelsPage.models
            spacing: Kirigami.Units.smallSpacing

            delegate: Kirigami.Card {
                width: ListView.view.width
                opacity: modelData.compatible !== false ? 1.0 : 0.6

                contentItem: RowLayout {
                    spacing: Kirigami.Units.largeSpacing

                    // Model info - left side (clickable for details)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        color: "transparent"

                        // MouseArea for showing details - only on the info section
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                modelDetailsDialog.modelId = modelData.id
                                modelDetailsDialog.modelName = modelData.name
                                modelDetailsDialog.open()
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: Kirigami.Units.smallSpacing

                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing
                                Layout.alignment: Qt.AlignVCenter

                                QQC2.Label {
                                    text: modelData.name || modelData.id
                                    font.bold: modelData.active
                                    font.pointSize: 10
                                }

                                // Backend badge
                                Rectangle {
                                    visible: modelData.backend !== undefined
                                    color: Kirigami.Theme.neutralBackgroundColor
                                    radius: 3
                                    Layout.preferredWidth: backendLabel.implicitWidth + 10
                                    Layout.preferredHeight: 18
                                    QQC2.Label {
                                        id: backendLabel
                                        anchors.centerIn: parent
                                        text: modelData.backend || ""
                                        font.pointSize: 7
                                        color: Kirigami.Theme.neutralTextColor
                                    }
                                }

                                // Active badge
                                Rectangle {
                                    visible: modelData.active
                                    color: Kirigami.Theme.positiveBackgroundColor
                                    radius: 3
                                    Layout.preferredWidth: 50
                                    Layout.preferredHeight: 18
                                    QQC2.Label {
                                        anchors.centerIn: parent
                                        text: "ACTIVE"
                                        font.pointSize: 7
                                        font.bold: true
                                        color: Kirigami.Theme.positiveTextColor
                                    }
                                }

                                // Recommended badge
                                Rectangle {
                                    visible: modelData.recommended && !modelData.active
                                    color: Kirigami.Theme.highlightColor
                                    radius: 3
                                    Layout.preferredWidth: 90
                                    Layout.preferredHeight: 18
                                    QQC2.Label {
                                        anchors.centerIn: parent
                                        text: "RECOMMENDED"
                                        font.pointSize: 7
                                        font.bold: true
                                        color: Kirigami.Theme.highlightedTextColor
                                    }
                                }

                                // Downloaded badge
                                Kirigami.Icon {
                                    visible: modelData.downloaded && !modelData.active
                                    source: "emblem-checked"
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                    color: Kirigami.Theme.positiveTextColor
                                }
                            }

                            // Size info with compatibility
                            RowLayout {
                                QQC2.Label {
                                    text: modelData.size
                                    font.pointSize: 9
                                    color: Kirigami.Theme.disabledTextColor
                                }

                                QQC2.Label {
                                    visible: modelData.compatible === false
                                    text: "⚠️ " + (modelData.compatibility_reason || "Not compatible")
                                    font.pointSize: 9
                                    color: Kirigami.Theme.negativeTextColor
                                }
                            }

                            // Download progress
                            QQC2.ProgressBar {
                                visible: downloadingModels[modelData.id] !== undefined || downloadingModels[modelData.name] !== undefined
                                Layout.fillWidth: true
                                Layout.maximumWidth: 200
                                from: 0
                                to: 100
                                value: downloadingModels[modelData.id] || downloadingModels[modelData.name] || 0
                            }
                        }
                    }

                    // Spacer
                    Item { Layout.fillWidth: true }

                    // Action buttons
                    RowLayout {
                        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                        spacing: Kirigami.Units.smallSpacing
                        Layout.preferredWidth: 350

                        QQC2.Button {
                            visible: !modelData.downloaded && downloadingModels[modelData.id] === undefined && downloadingModels[modelData.name] === undefined
                            text: "Download"
                            icon.name: "download"
                            Layout.preferredWidth: 80
                            enabled: modelData.compatible !== false
                            onClicked: settingsBridge.downloadModel(modelData.id)
                        }

                        QQC2.Button {
                            visible: modelData.downloaded && !modelData.active
                            text: "Activate"
                            icon.name: "run-build"
                            Layout.preferredWidth: 80
                            onClicked: {
                                settingsBridge.setActiveModel(modelData.id)
                                refreshModels()
                            }
                        }

                        QQC2.Button {
                            visible: modelData.downloaded && !modelData.active
                            text: "Delete"
                            icon.name: "delete"
                            Layout.preferredWidth: 80
                            onClicked: {
                                deleteDialog.modelId = modelData.id
                                deleteDialog.modelName = modelData.name
                                deleteDialog.open()
                            }
                        }

                        QQC2.Button {
                            text: "Details"
                            icon.name: "documentinfo"
                            Layout.preferredWidth: 80
                            onClicked: {
                                modelDetailsDialog.modelId = modelData.id
                                modelDetailsDialog.modelName = modelData.name
                                modelDetailsDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    // Delete confirmation dialog
    Kirigami.Dialog {
        id: deleteDialog
        property string modelId: ""
        property string modelName: ""
        
        title: "Delete Model"
        standardButtons: Kirigami.Dialog.Ok | Kirigami.Dialog.Cancel
        
        onAccepted: {
            settingsBridge.deleteModel(modelId)
            refreshModels()
        }
        
        QQC2.Label {
            text: "Are you sure you want to delete '" + deleteDialog.modelName + "'?"
            wrapMode: Text.WordWrap
        }
    }

    // Model Details Dialog
    Kirigami.Dialog {
        id: modelDetailsDialog
        property string modelId: ""
        property string modelName: ""
        property var details: ({})

        title: modelName + " Details"

        onOpened: {
            details = settingsBridge.getModelDetails(modelId)
        }

        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            // Description
            QQC2.Label {
                Layout.fillWidth: true
                text: details.description || ""
                wrapMode: Text.WordWrap
                visible: details.description !== undefined
            }

            // Hardware Requirements
            Kirigami.Separator {
                Layout.fillWidth: true
            }

            Kirigami.Heading {
                text: "Hardware Requirements"
                level: 4
            }

            GridLayout {
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing

                QQC2.Label {
                    text: "Size:"
                    font.bold: true
                }
                QQC2.Label {
                    text: details.size || "Unknown"
                }

                QQC2.Label {
                    text: "Min RAM:"
                    font.bold: true
                }
                QQC2.Label {
                    text: (details.min_ram_gb || "?") + " GB"
                }

                QQC2.Label {
                    text: "Recommended RAM:"
                    font.bold: true
                }
                QQC2.Label {
                    text: (details.recommended_ram_gb || "?") + " GB"
                }

                QQC2.Label {
                    text: "Min VRAM:"
                    font.bold: true
                }
                QQC2.Label {
                    text: details.min_vram_gb ? details.min_vram_gb + " GB" : "None (CPU compatible)"
                }

                QQC2.Label {
                    text: "GPU Preference:"
                    font.bold: true
                }
                QQC2.Label {
                    text: details.gpu_preference || "Unknown"
                    color: details.gpu_preference_raw === "gpu_agnostic" ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.neutralTextColor
                }
            }

            // Language Performance
            Kirigami.Separator {
                Layout.fillWidth: true
                visible: Object.keys(details.language_performance || {}).length > 0
            }

            Kirigami.Heading {
                text: "Language Performance"
                level: 4
                visible: Object.keys(details.language_performance || {}).length > 0
            }

            ColumnLayout {
                visible: Object.keys(details.language_performance || {}).length > 0
                spacing: Kirigami.Units.smallSpacing

                Repeater {
                    model: Object.keys(details.language_performance || {})
                    delegate: RowLayout {
                        QQC2.Label {
                            text: modelData + ":"
                            Layout.preferredWidth: 120
                        }
                        QQC2.ProgressBar {
                            from: 0
                            to: 100
                            value: parseInt(details.language_performance[modelData])
                            Layout.fillWidth: true
                        }
                        QQC2.Label {
                            text: details.language_performance[modelData]
                            Layout.preferredWidth: 40
                        }
                    }
                }
            }

            // Languages Supported
            Kirigami.Separator {
                Layout.fillWidth: true
            }

            Kirigami.Heading {
                text: "Languages Supported"
                level: 4
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: (details.languages || []).join(", ")
                wrapMode: Text.WordWrap
            }

            // Features
            Kirigami.Separator {
                Layout.fillWidth: true
            }

            Kirigami.Heading {
                text: "Features"
                level: 4
            }

            ColumnLayout {
                spacing: Kirigami.Units.smallSpacing

                QQC2.Label {
                    text: details.supports_word_timestamps ? "✓ Word timestamps" : "✗ Word timestamps"
                    color: details.supports_word_timestamps ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.disabledTextColor
                }

                QQC2.Label {
                    text: details.is_streaming ? "✓ Streaming support" : "✗ Streaming support"
                    color: details.is_streaming ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.disabledTextColor
                }

                QQC2.Label {
                    text: "License: " + (details.license || "Unknown")
                }
            }

            // Compatibility Status
            Kirigami.Separator {
                Layout.fillWidth: true
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                text: details.compatible !== false ? "Compatible with your system" : (details.compatibility_reason || "Not compatible")
                type: details.compatible !== false ? Kirigami.MessageType.Positive : Kirigami.MessageType.Warning
                visible: true
            }

            QQC2.Label {
                visible: details.recommended
                text: "⭐ Recommended for your system"
                font.bold: true
                color: Kirigami.Theme.positiveTextColor
            }
        }

        footer: RowLayout {
            spacing: Kirigami.Units.largeSpacing
            Layout.alignment: Qt.AlignRight

            Item { Layout.fillWidth: true }

            QQC2.Button {
                text: "Download"
                icon.name: "download"
                visible: details.downloaded === false && !downloadingModels[modelDetailsDialog.modelId]
                enabled: details.compatible !== false
                onClicked: {
                    settingsBridge.downloadModel(modelDetailsDialog.modelId)
                    modelDetailsDialog.close()
                }
            }

            QQC2.Button {
                text: "Activate"
                icon.name: "run-build"
                visible: details.downloaded === true && details.active !== true
                onClicked: {
                    settingsBridge.setActiveModel(modelDetailsDialog.modelId)
                    refreshModels()
                    modelDetailsDialog.close()
                }
            }
            
            QQC2.Button {
                text: "Close"
                onClicked: modelDetailsDialog.close()
            }
        }
    }

    // Dependency Install Dialog
    Kirigami.Dialog {
        id: dependencyInstallDialog
        property string modelId: ""
        property string backend: ""
        property string statusMessage: ""
        property int progress: 0
        property bool installing: false
        
        title: "Install " + backend + " Backend"
        
        onOpened: {
            installing = false
            progress = 0
            statusMessage = ""
        }
        
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing
            
            QQC2.Label {
                Layout.fillWidth: true
                text: "The " + dependencyInstallDialog.backend + " backend requires additional dependencies to be installed."
                wrapMode: Text.WordWrap
            }
            
            Kirigami.Separator {
                Layout.fillWidth: true
            }
            
            QQC2.Label {
                Layout.fillWidth: true
                text: "Required packages:"
                font.bold: true
            }
            
            QQC2.Label {
                Layout.fillWidth: true
                text: {
                    var info = settingsBridge.getBackendDependencyInfo(dependencyInstallDialog.backend)
                    return info.packages ? info.packages.join(", ") : "Unknown"
                }
                wrapMode: Text.WordWrap
                font.family: "monospace"
            }
            
            QQC2.Label {
                Layout.fillWidth: true
                text: {
                    var info = settingsBridge.getBackendDependencyInfo(dependencyInstallDialog.backend)
                    return "Estimated download size: " + (info.size_estimate || "Unknown")
                }
                color: Kirigami.Theme.disabledTextColor
            }
            
            // Progress section (visible during install)
            ColumnLayout {
                Layout.fillWidth: true
                visible: dependencyInstallDialog.installing
                spacing: Kirigami.Units.smallSpacing
                
                QQC2.ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: dependencyInstallDialog.progress
                }
                
                QQC2.Label {
                    Layout.fillWidth: true
                    text: dependencyInstallDialog.statusMessage
                    wrapMode: Text.WordWrap
                }
            }
            
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !dependencyInstallDialog.installing && dependencyInstallDialog.statusMessage !== ""
                text: dependencyInstallDialog.statusMessage
                type: Kirigami.MessageType.Error
            }
        }
        
        footer: RowLayout {
            spacing: Kirigami.Units.largeSpacing
            
            Item { Layout.fillWidth: true }
            
            QQC2.Button {
                text: "Cancel"
                visible: !dependencyInstallDialog.installing
                onClicked: dependencyInstallDialog.close()
            }
            
            QQC2.Button {
                text: "Install"
                visible: !dependencyInstallDialog.installing
                icon.name: "download"
                onClicked: {
                    dependencyInstallDialog.installing = true
                    dependencyInstallDialog.statusMessage = "Starting installation..."
                    settingsBridge.installBackendDependencies(dependencyInstallDialog.backend)
                }
            }
            
            QQC2.Button {
                text: "Installing..."
                visible: dependencyInstallDialog.installing
                enabled: false
                icon.name: "content-loading"
            }
        }
    }
}
