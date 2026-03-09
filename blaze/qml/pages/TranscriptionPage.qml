import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    spacing: Kirigami.Units.largeSpacing

    Component.onCompleted: {
        // Load General settings
        var languages = settingsBridge.getAvailableLanguages()
        var currentLang = settingsBridge.getLanguage()
        for (var i = 0; i < languages.length; i++) {
            languageCombo.model.append(languages[i])
            if (languages[i].code === currentLang) {
                languageCombo.currentIndex = i
            }
        }

        var device = settingsBridge.getDevice()
        deviceCombo.currentIndex = (device === "cpu") ? 0 : 1

        // Load Whisper settings
        var computeType = settingsBridge.getComputeType()
        if (computeType === "float32") computeTypeCombo.currentIndex = 0
        else if (computeType === "float16") computeTypeCombo.currentIndex = 1
        else if (computeType === "int8") computeTypeCombo.currentIndex = 2

        beamSizeSpin.value = settingsBridge.getBeamSize()
        vadCheck.checked = settingsBridge.getVadFilter()
        timestampsCheck.checked = settingsBridge.getWordTimestamps()

        // Load Liquid settings
        var liquidSettings = settingsBridge.getLiquidSettings()
        liquidTempSlider.value = liquidSettings.temperature * 100  // Convert 0-1 to 0-100
        liquidTopKSpin.value = liquidSettings.top_k
        liquidMaxTokensSpin.value = liquidSettings.max_tokens

        // Load Qwen settings
        var qwenSettings = settingsBridge.getQwenSettings()
        qwenTempSlider.value = qwenSettings.temperature * 100  // Convert 0-1 to 0-100
        qwenTopPSlider.value = qwenSettings.top_p * 100  // Convert 0-1 to 0-100
        qwenTopKSpin.value = qwenSettings.top_k
        qwenMaxTokensSpin.value = qwenSettings.max_tokens
        qwenRepetitionPenaltySpin.value = qwenSettings.repetition_penalty * 10  // Convert 1.0-2.0 to 10-20

        // Load Qwen device setting
        var qwenDevice = settingsBridge.getQwenDevice()
        qwenDeviceCombo.currentIndex = (qwenDevice === "cpu") ? 0 : 1
    }

    // Page header
    Kirigami.Heading {
        text: "Transcription Settings"
        level: 1
    }

    QQC2.Label {
        Layout.fillWidth: true
        text: "Configure language and backend-specific transcription options"
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.disabledTextColor
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }

    // Tab bar
    QQC2.TabBar {
        id: tabBar
        Layout.fillWidth: true

        QQC2.TabButton {
            text: "General"
        }
        QQC2.TabButton {
            text: "Whisper"
        }
        QQC2.TabButton {
            text: "Liquid"
        }
        QQC2.TabButton {
            text: "Qwen"
        }
    }

    // Tab content
    StackLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: tabBar.currentIndex

        // ===== GENERAL TAB =====
        Kirigami.ScrollablePage {
            Kirigami.FormLayout {
                anchors.fill: parent

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
                    id: deviceCombo
                    Kirigami.FormData.label: "Device:"
                    model: ["CPU", "CUDA (GPU)"]
                    currentIndex: 0

                    onActivated: {
                        settingsBridge.setDevice(currentIndex === 0 ? "cpu" : "cuda")
                    }
                }
            }
        }

        // ===== WHISPER TAB =====
        Kirigami.ScrollablePage {
            Kirigami.FormLayout {
                anchors.fill: parent

                QQC2.ComboBox {
                    id: computeTypeCombo
                    Kirigami.FormData.label: "Compute Type:"
                    model: ["float32", "float16", "int8"]
                    currentIndex: 0

                    onActivated: {
                        settingsBridge.setComputeType(model[currentIndex])
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

                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.largeSpacing
                    type: Kirigami.MessageType.Information
                    text: "VAD (Voice Activity Detection) helps improve accuracy by filtering out silence and background noise."
                    visible: true
                }
            }
        }

        // ===== LIQUID TAB =====
        Kirigami.ScrollablePage {
            Kirigami.FormLayout {
                anchors.fill: parent

                QQC2.Slider {
                    id: liquidTempSlider
                    Kirigami.FormData.label: "Temperature: " + (value / 100).toFixed(2)
                    from: 0
                    to: 100
                    value: 30
                    stepSize: 5
                    snapMode: QQC2.Slider.SnapAlways

                    onMoved: {
                        settingsBridge.setLiquidTemperature(value / 100)
                    }
                }

                QQC2.Label {
                    Layout.fillWidth: true
                    text: "Lower = more deterministic, less hallucination. Higher = more creative."
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.disabledTextColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.SpinBox {
                    id: liquidTopKSpin
                    Kirigami.FormData.label: "Top-K:"
                    from: 1
                    to: 100
                    value: 50

                    onValueModified: {
                        settingsBridge.setLiquidTopK(value)
                    }
                }

                QQC2.SpinBox {
                    id: liquidMaxTokensSpin
                    Kirigami.FormData.label: "Max Tokens:"
                    from: 100
                    to: 2048
                    value: 1024

                    onValueModified: {
                        settingsBridge.setLiquidMaxTokens(value)
                    }
                }

                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.largeSpacing
                    type: Kirigami.MessageType.Information
                    text: "These settings only apply to the Liquid AI LFM2.5-Audio model. Temperature affects creativity vs accuracy."
                    visible: true
                }
            }
        }

        // ===== QWEN TAB =====
        Kirigami.ScrollablePage {
            Kirigami.FormLayout {
                anchors.fill: parent

                QQC2.ComboBox {
                    id: qwenDeviceCombo
                    Kirigami.FormData.label: "Device:"
                    model: ["CPU", "CUDA (GPU)"]
                    currentIndex: 1

                    onActivated: {
                        settingsBridge.setQwenDevice(currentIndex === 0 ? "cpu" : "cuda")
                    }
                }

                QQC2.Slider {
                    id: qwenTempSlider
                    Kirigami.FormData.label: "Temperature: " + (value / 100).toFixed(2)
                    from: 0
                    to: 100
                    value: 70
                    stepSize: 5
                    snapMode: QQC2.Slider.SnapAlways

                    onMoved: {
                        settingsBridge.setQwenTemperature(value / 100)
                    }
                }

                QQC2.Label {
                    Layout.fillWidth: true
                    text: "Lower = more deterministic. Higher = more creative. Recommended: 0.7"
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.disabledTextColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.Slider {
                    id: qwenTopPSlider
                    Kirigami.FormData.label: "Top-P: " + (value / 100).toFixed(2)
                    from: 10
                    to: 100
                    value: 90
                    stepSize: 5
                    snapMode: QQC2.Slider.SnapAlways

                    onMoved: {
                        settingsBridge.setQwenTopP(value / 100)
                    }
                }

                QQC2.Label {
                    Layout.fillWidth: true
                    text: "Nucleus sampling threshold. Lower = more focused. Recommended: 0.9"
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.disabledTextColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                QQC2.SpinBox {
                    id: qwenTopKSpin
                    Kirigami.FormData.label: "Top-K:"
                    from: 1
                    to: 100
                    value: 50

                    onValueModified: {
                        settingsBridge.setQwenTopK(value)
                    }
                }

                QQC2.SpinBox {
                    id: qwenMaxTokensSpin
                    Kirigami.FormData.label: "Max Tokens:"
                    from: 50
                    to: 500
                    value: 256

                    onValueModified: {
                        settingsBridge.setQwenMaxTokens(value)
                    }
                }

                QQC2.SpinBox {
                    id: qwenRepetitionPenaltySpin
                    Kirigami.FormData.label: "Repetition Penalty:"
                    from: 10
                    to: 20
                    value: 11
                    stepSize: 1
                    textFromValue: function(value, locale) {
                        return (value / 10).toFixed(1)
                    }
                    valueFromText: function(text, locale) {
                        return parseFloat(text) * 10
                    }

                    onValueModified: {
                        settingsBridge.setQwenRepetitionPenalty(value / 10)
                    }
                }

                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.largeSpacing
                    type: Kirigami.MessageType.Information
                    text: "These settings apply to Qwen2-Audio models. Temperature, Top-P, and Top-K control text generation diversity."
                    visible: true
                }
            }
        }
    }
}
