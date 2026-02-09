import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import org.kde.kirigami 2.20 as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: "Kirigami Test Window"
    width: 400
    height: 300
    
    Kirigami.Page {
        anchors.fill: parent
        
        Kirigami.FormLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            
            Kirigami.Label {
                text: "Kirigami Integration Test"
                font.pointSize: 16
                Kirigami.FormData.label: "Test:"
            }
            
            Kirigami.TextField {
                id: testField
                placeholderText: "Type something..."
                Kirigami.FormData.label: "Text Field:"
            }
            
            Kirigami.Button {
                text: "Test Button"
                Kirigami.FormData.label: "Button:"
                
                onClicked: {
                    console.log("Button clicked! Text:", testField.text)
                    
                    // Test Python-QML bridge
                    if (settingsBridge) {
                        let testValue = settingsBridge.get("test_setting")
                        console.log("Test setting from Python:", testValue)
                    }
                }
            }
            
            Kirigami.Label {
                text: "This is a Kirigami component test"
                wrapMode: Text.WordWrap
                Kirigami.FormData.label: "Status:"
            }
        }
    }
    
    Component.onCompleted: {
        console.log("Kirigami test window loaded successfully!")
        console.log("Kirigami theme:", Kirigami.Theme.colorSet)
        console.log("Kirigami units:", Kirigami.Units.largeSpacing)
    }
}