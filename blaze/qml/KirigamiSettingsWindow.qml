import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    title: "Syllablaze Settings"
    width: 600
    height: 500
    
    TabBar {
        id: tabBar
        width: parent.width
        
        TabButton { text: "Models" }
        TabButton { text: "Audio" }
        TabButton { text: "Transcription" }
        TabButton { text: "Shortcuts" }
        TabButton { text: "About" }
    }
    
    StackLayout {
        width: parent.width
        height: parent.height - tabBar.height
        y: tabBar.height
        currentIndex: tabBar.currentIndex
        
        // Models Tab
        ScrollView {
            ColumnLayout {
                width: parent.width
                spacing: 10
                
                Label {
                    text: "Whisper Models"
                    font.bold: true
                    Layout.alignment: Qt.AlignCenter
                }
                
                ComboBox {
                    id: modelComboBox
                    model: ["tiny", "base", "small", "medium", "large"]
                    Layout.fillWidth: true
                    
                    onCurrentTextChanged: {
                        if (settingsBridge) {
                            settingsBridge.set("model", currentText)
                        }
                    }
                }
            }
        }
        
        // Audio Tab
        ScrollView {
            ColumnLayout {
                width: parent.width
                anchors.margins: 10
                
                Label { text: "Audio Settings"; font.bold: true; Layout.alignment: Qt.AlignCenter }
                
                Label { text: "Input Device:" }
                ComboBox {
                    id: audioDeviceComboBox
                    model: audioBridge ? audioBridge.getAudioDevices() : []
                    Layout.fillWidth: true
                }
                
                Label { text: "Sample Rate:" }
                ComboBox {
                    id: sampleRateComboBox
                    model: ["16kHz - best for Whisper", "Default for device"]
                    Layout.fillWidth: true
                }
            }
        }
        
        // Transcription Tab
        ScrollView {
            ColumnLayout {
                width: parent.width
                anchors.margins: 10
                
                Label { text: "Transcription Settings"; font.bold: true; Layout.alignment: Qt.AlignCenter }
                
                Label { text: "Language:" }
                ComboBox {
                    id: languageComboBox
                    model: ["auto", "English", "Spanish", "French", "German"]
                    Layout.fillWidth: true
                }
                
                Label { text: "Compute Type:" }
                ComboBox {
                    id: computeTypeComboBox
                    model: ["float32", "float16", "int8"]
                    Layout.fillWidth: true
                }
            }
        }
        
        // Shortcuts Tab
        ScrollView {
            ColumnLayout {
                width: parent.width
                
                Label {
                    text: "Toggle Recording:"
                    Layout.alignment: Qt.AlignCenter
                }
                
                Label {
                    text: "Alt+Space (configured in KDE System Settings)"
                    Layout.alignment: Qt.AlignCenter
                }
            }
        }
        
        // About Tab
        ScrollView {
            ColumnLayout {
                width: parent.width
                
                Label {
                    text: "Syllablaze"
                    font.bold: true
                    font.pointSize: 16
                    Layout.alignment: Qt.AlignCenter
                }
                
                Label {
                    text: "Version 0.5"
                    Layout.alignment: Qt.AlignCenter
                }
                
                Button {
                    text: "GitHub Repository"
                    Layout.alignment: Qt.AlignCenter
                    
                    onClicked: {
                        Qt.openUrlExternally("https://github.com/Zebastjan/Syllablaze")
                    }
                }
            }
        }
    }
    
    Component.onCompleted: {
        console.log("KirigamiSettingsWindow loaded")
    }
}