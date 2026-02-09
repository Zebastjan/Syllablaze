import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    Component.onCompleted: {
        // Load current settings
        var languages = settingsBridge.getAvailableLanguages()
        var currentLang = settingsBridge.getLanguage()

        // Populate language combo
        for (var i = 0; i < languages.length; i++) {
            languageCombo.model.append(languages[i])
            if (languages[i].code === currentLang) {
                languageCombo.currentIndex = i
            }
        }

        // Set other controls
        var computeType = settingsBridge.getComputeType()
        if (computeType === "float32") computeTypeCombo.currentIndex = 0
        else if (computeType === "float16") computeTypeCombo.currentIndex = 1
        else if (computeType === "int8") computeTypeCombo.currentIndex = 2

        var device = settingsBridge.getDevice()
        deviceCombo.currentIndex = (device === "cpu") ? 0 : 1

        beamSizeSpin.value = settingsBridge.getBeamSize()
        vadCheck.checked = settingsBridge.getVadFilter()
        timestampsCheck.checked = settingsBridge.getWordTimestamps()
    }

    // Page header
    Kirigami.Heading {
        text: "Transcription Settings"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Configure language and transcription options"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Settings form
    Kirigami.FormLayout {
        Layout.fillWidth: true

        QQC2.ComboBox {
            id: languageCombo
            Kirigami.FormData.label: "Language:"
            textRole: "name"
            model: ListModel {}

            onActivated: {
                var lang = model.get(currentIndex)
                settingsBridge.setLanguage(lang.code)
            }
        }

        QQC2.ComboBox {
            id: computeTypeCombo
            Kirigami.FormData.label: "Compute Type:"
            model: ["float32", "float16", "int8"]
            currentIndex: 0

            onActivated: {
                settingsBridge.setComputeType(model[currentIndex])
            }
        }

        QQC2.ComboBox {
            id: deviceCombo
            Kirigami.FormData.label: "Device:"
            model: ["CPU", "CUDA (GPU)"]
            currentIndex: 0

            onActivated: {
                if (currentIndex === 0) {
                    settingsBridge.setDevice("cpu")
                } else {
                    settingsBridge.setDevice("cuda")
                }
            }
        }

        QQC2.SpinBox {
            id: beamSizeSpin
            Kirigami.FormData.label: "Beam Size:"
            from: 1
            to: 10
            value: 5

            onValueModified: {
                settingsBridge.setBeamSize(value)
            }
        }

        QQC2.CheckBox {
            id: vadCheck
            Kirigami.FormData.label: "Voice Activity Detection:"
            text: "Use VAD filter to remove silence"
            checked: true

            onToggled: {
                settingsBridge.setVadFilter(checked)
            }
        }

        QQC2.CheckBox {
            id: timestampsCheck
            Kirigami.FormData.label: "Word Timestamps:"
            text: "Generate word-level timestamps"
            checked: false

            onToggled: {
                settingsBridge.setWordTimestamps(checked)
            }
        }
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        type: Kirigami.MessageType.Information
        text: "VAD (Voice Activity Detection) helps improve accuracy by filtering out silence and background noise."
        visible: true
    }

    Item {
        Layout.fillHeight: true
    }
}
