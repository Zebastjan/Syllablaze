import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import org.kde.kirigami 2.20 as Kirigami

ApplicationWindow {
    id: root
    title: "Syllablaze Settings"
    width: 800
    height: 600
    
    // Use KDE Breeze theme
    Kirigami.Theme.colorSet: Kirigami.Theme.View
    
    pageStack.initialPage: Kirigami.ScrollablePage {
        title: "Syllablaze Settings"
        
        FormLayout {
            id: formLayout
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            
            Kirigami.Separator {
                Kirigami.FormData.label: "Models"
                Kirigami.FormData.isSection: true
            }
            
            Kirigami.Label {
                text: "Whisper Models"
                Kirigami.FormData.label: "Active Model:"
            }
            
            Kirigami.ComboBox {
                id: modelComboBox
                model: ["tiny", "base", "small", "medium", "large"]
                Kirigami.FormData.label: "Select Model:"
                
                onCurrentTextChanged: {
                    if (settingsBridge) {
                        settingsBridge.set("model", currentText)
                    }
                }
            }
            
            Kirigami.Separator {
                Kirigami.FormData.label: "Audio Settings"
                Kirigami.FormData.isSection: true
            }
            
            Kirigami.ComboBox {
                id: audioDeviceComboBox
                model: audioBridge ? audioBridge.getAudioDevices() : []
                Kirigami.FormData.label: "Input Device:"
                
                onCurrentIndexChanged: {
                    if (settingsBridge && currentIndex >= 0) {
                        settingsBridge.set("mic_index", currentIndex)
                    }
                }
            }
            
            Kirigami.ComboBox {
                id: sampleRateComboBox
                model: ["16kHz - best for Whisper", "Default for device"]
                Kirigami.FormData.label: "Sample Rate:"
                
                onCurrentIndexChanged: {
                    if (settingsBridge) {
                        let mode = currentIndex === 0 ? "whisper" : "device"
                        settingsBridge.set("sample_rate_mode", mode)
                    }
                }
            }
            
            Kirigami.Separator {
                Kirigami.FormData.label: "Transcription Settings"
                Kirigami.FormData.isSection: true
            }
            
            Kirigami.ComboBox {
                id: languageComboBox
                model: settingsBridge ? settingsBridge.getAvailableLanguages() : []
                textRole: "value"
                Kirigami.FormData.label: "Language:"
                
                onCurrentIndexChanged: {
                    if (settingsBridge && currentIndex >= 0) {
                        let languageCode = model[currentIndex].key
                        settingsBridge.set("language", languageCode)
                    }
                }
            }
            
            Kirigami.ComboBox {
                id: computeTypeComboBox
                model: ["float32", "float16", "int8"]
                Kirigami.FormData.label: "Compute Type:"
                
                onCurrentTextChanged: {
                    if (settingsBridge) {
                        settingsBridge.set("compute_type", currentText)
                    }
                }
            }
            
            Kirigami.ComboBox {
                id: deviceComboBox
                model: ["cpu", "cuda"]
                Kirigami.FormData.label: "Device:"
                
                onCurrentTextChanged: {
                    if (settingsBridge) {
                        settingsBridge.set("device", currentText)
                    }
                }
            }
            
            Kirigami.SpinBox {
                id: beamSizeSpinBox
                from: 1
                to: 10
                Kirigami.FormData.label: "Beam Size:"
                
                onValueChanged: {
                    if (settingsBridge) {
                        settingsBridge.set("beam_size", value)
                    }
                }
            }
            
            Kirigami.CheckBox {
                id: vadFilterCheckBox
                text: "Use Voice Activity Detection (VAD) filter"
                
                onCheckedChanged: {
                    if (settingsBridge) {
                        settingsBridge.set("vad_filter", checked)
                    }
                }
            }
            
            Kirigami.CheckBox {
                id: wordTimestampsCheckBox
                text: "Generate word timestamps"
                
                onCheckedChanged: {
                    if (settingsBridge) {
                        settingsBridge.set("word_timestamps", checked)
                    }
                }
            }
            
            Kirigami.Separator {
                Kirigami.FormData.label: "Shortcuts"
                Kirigami.FormData.isSection: true
            }
            
            Kirigami.Label {
                text: "Shortcuts are managed by KDE System Settings"
                wrapMode: Text.WordWrap
                Kirigami.FormData.label: "Toggle Recording:"
            }
            
            Kirigami.Button {
                text: "Open KDE System Settings"
                Kirigami.FormData.label: "Configure:"
                
                onClicked: {
                    // This would open KDE System Settings
                    console.log("Opening KDE System Settings...")
                }
            }
            
            Kirigami.Separator {
                Kirigami.FormData.label: "About"
                Kirigami.FormData.isSection: true
            }
            
            Kirigami.Label {
                text: "Syllablaze v0.5"
                Kirigami.FormData.label: "Version:"
            }
            
            Kirigami.Button {
                text: "GitHub Repository"
                Kirigami.FormData.label: "Source:"
                
                onClicked: {
                    Qt.openUrlExternally("https://github.com/Zebastjan/Syllablaze")
                }
            }
        }
    }
    
    Component.onCompleted: {
        // Initialize settings from Python backend
        if (settingsBridge) {
            // Set initial values
            let currentModel = settingsBridge.get("model")
            if (currentModel && modelComboBox.model.indexOf(currentModel) >= 0) {
                modelComboBox.currentIndex = modelComboBox.model.indexOf(currentModel)
            }
            
            let currentLanguage = settingsBridge.get("language")
            // Language initialization would be more complex
            
            console.log("SettingsWindow initialized with Kirigami")
        }
    }
}