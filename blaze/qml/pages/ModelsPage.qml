import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
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

    property var models: []
    property var downloadingModels: ({})
    property var hardwareInfo: ({})
    property var recommendedModel: ({})

    Component.onCompleted: {
        refreshModels()
        refreshHardwareInfo()
        settingsBridge.modelDownloadProgress.connect(onDownloadProgress)
        settingsBridge.modelDownloadComplete.connect(onDownloadComplete)
        settingsBridge.modelDownloadError.connect(onDownloadError)
    }

    function refreshModels() {
        models = settingsBridge.getAvailableModels()
    }

    function refreshHardwareInfo() {
        hardwareInfo = settingsBridge.getHardwareInfo()
        recommendedModel = settingsBridge.getRecommendedModel()
    }

    function onDownloadProgress(modelName, progress) {
        downloadingModels[modelName] = progress
        downloadingModelsChanged()
    }

    function onDownloadComplete(modelName) {
        delete downloadingModels[modelName]
        downloadingModelsChanged()
        refreshModels()
        inlineMessage.text = "Download complete: " + modelName
        inlineMessage.type = Kirigami.MessageType.Positive
        inlineMessage.visible = true
    }

    function onDownloadError(modelName, error) {
        delete downloadingModels[modelName]
        downloadingModelsChanged()
        inlineMessage.text = "Download failed: " + error
        inlineMessage.type = Kirigami.MessageType.Error
        inlineMessage.visible = true
    }

    // Hardware Info Card
    Kirigami.Card {
        Layout.fillWidth: true
        visible: hardwareInfo.total_ram_gb !== undefined
        
        contentItem: ColumnLayout {
            Kirigami.Heading {
                text: "Your System"
                level: 3
            }
            
            RowLayout {
                QQC2.Label {
                    text: "💻 RAM: " + (hardwareInfo.available_ram_gb || "?") + " GB available / " + (hardwareInfo.total_ram_gb || "?") + " GB total"
                }
                
                QQC2.Label {
                    visible: hardwareInfo.gpu_available
                    text: " | 🎮 GPU: " + (hardwareInfo.gpu_count || 0) + " device(s)"
                    color: Kirigami.Theme.positiveTextColor
                }
                
                QQC2.Label {
                    visible: !hardwareInfo.gpu_available
                    text: " | CPU only"
                    color: Kirigami.Theme.disabledTextColor
                }
            }
            
            QQC2.Label {
                visible: recommendedModel.id !== undefined
                text: "⭐ Recommended: " + (recommendedModel.name || "")
                font.bold: true
                color: Kirigami.Theme.positiveTextColor
            }
        }
    }

    Kirigami.InlineMessage {
        id: inlineMessage
        Layout.fillWidth: true
        visible: false
        showCloseButton: true
    }

    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true

        ListView {
            model: models
            spacing: Kirigami.Units.smallSpacing

            delegate: Kirigami.Card {
                width: ListView.view.width
                opacity: modelData.compatible !== false ? 1.0 : 0.6
                
                contentItem: RowLayout {
                    spacing: Kirigami.Units.largeSpacing

                    // Model info - left side
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
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
                        
                        // Description
                        QQC2.Label {
                            text: modelData.description || ""
                            font.pointSize: 9
                            color: Kirigami.Theme.textColor
                            visible: modelData.description !== undefined
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
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
                            visible: downloadingModels[modelData.name || modelData.id] !== undefined
                            Layout.fillWidth: true
                            Layout.maximumWidth: 200
                            from: 0
                            to: 100
                            value: downloadingModels[modelData.name || modelData.id] || 0
                        }
                    }

                    // Spacer to push buttons right
                    Item { Layout.fillWidth: true }

                    // Action buttons - right side, vertically centered
                    RowLayout {
                        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                        spacing: Kirigami.Units.smallSpacing
                        Layout.preferredWidth: 280

                        QQC2.Button {
                            visible: !modelData.downloaded && !downloadingModels[modelData.name || modelData.id]
                            text: "Download"
                            icon.name: "download"
                            Layout.preferredWidth: 90
                            enabled: modelData.compatible !== false
                            onClicked: settingsBridge.downloadModel(modelData.name || modelData.id)
                        }

                        QQC2.Button {
                            visible: modelData.downloaded && !modelData.active
                            text: "Activate"
                            icon.name: "run-build"
                            Layout.preferredWidth: 90
                            onClicked: {
                                settingsBridge.setActiveModel(modelData.name || modelData.id)
                                refreshModels()
                            }
                        }

                        QQC2.Button {
                            visible: modelData.downloaded && !modelData.active
                            text: "Delete"
                            icon.name: "delete"
                            Layout.preferredWidth: 90
                            onClicked: {
                                deleteDialog.modelName = modelData.name || modelData.id
                                deleteDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    Kirigami.PromptDialog {
        id: deleteDialog
        property string modelName: ""
        title: "Delete Model"
        subtitle: "Delete " + modelName + "?"
        standardButtons: Kirigami.Dialog.Ok | Kirigami.Dialog.Cancel
        onAccepted: {
            settingsBridge.deleteModel(modelName)
            refreshModels()
        }
    }

    Kirigami.Card {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.largeSpacing
        contentItem: ColumnLayout {
            Kirigami.Heading {
                text: "Model Information"
                level: 3
            }
            QQC2.Label {
                Layout.fillWidth: true
                text: "• Larger models = better accuracy but require more RAM\n" +
                      "• *.en models are optimized for English speech\n" +
                      "• Distil models are faster with slightly lower accuracy\n" +
                      "• Models are downloaded to: ~/.cache/whisper/\n" +
                      "• Compatible models work with your current hardware\n" +
                      "• Recommended models provide the best experience for your system"
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
            }
        }
    }
}
