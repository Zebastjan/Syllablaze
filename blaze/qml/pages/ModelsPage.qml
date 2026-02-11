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

    property var models: []
    property var downloadingModels: ({})

    Component.onCompleted: {
        refreshModels()
        settingsBridge.modelDownloadProgress.connect(onDownloadProgress)
        settingsBridge.modelDownloadComplete.connect(onDownloadComplete)
        settingsBridge.modelDownloadError.connect(onDownloadError)
    }

    function refreshModels() {
        models = settingsBridge.getAvailableModels()
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
                                text: modelData.name
                                font.bold: modelData.active
                                font.pointSize: 10
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

                            // Downloaded badge
                            Kirigami.Icon {
                                visible: modelData.downloaded && !modelData.active
                                source: "emblem-checked"
                                Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                color: Kirigami.Theme.positiveTextColor
                            }
                        }

                        // Size info
                        QQC2.Label {
                            text: modelData.size
                            font.pointSize: 9
                            color: Kirigami.Theme.disabledTextColor
                        }

                        // Download progress
                        QQC2.ProgressBar {
                            visible: downloadingModels[modelData.name] !== undefined
                            Layout.fillWidth: true
                            Layout.maximumWidth: 200
                            from: 0
                            to: 100
                            value: downloadingModels[modelData.name] || 0
                        }
                    }

                    // Spacer to push buttons right
                    Item { Layout.fillWidth: true }

                    // Action buttons - right side, vertically centered
                    RowLayout {
                        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                        spacing: Kirigami.Units.smallSpacing
                        Layout.preferredWidth: 280  // Fixed width for alignment

                        QQC2.Button {
                            visible: !modelData.downloaded && !downloadingModels[modelData.name]
                            text: "Download"
                            icon.name: "download"
                            Layout.preferredWidth: 90
                            onClicked: settingsBridge.downloadModel(modelData.name)
                        }

                        QQC2.Button {
                            visible: modelData.downloaded && !modelData.active
                            text: "Activate"
                            icon.name: "run-build"
                            Layout.preferredWidth: 90
                            onClicked: {
                                settingsBridge.setActiveModel(modelData.name)
                                refreshModels()
                            }
                        }

                        QQC2.Button {
                            visible: modelData.downloaded && !modelData.active
                            text: "Delete"
                            icon.name: "delete"
                            Layout.preferredWidth: 90
                            onClicked: {
                                deleteDialog.modelName = modelData.name
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
                text: "• Larger models = better accuracy + more VRAM\n• *.en models are faster for English\n• Distil models = optimized for speed\n• Cache: ~/.cache/whisper/"
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
            }
        }
    }
}
