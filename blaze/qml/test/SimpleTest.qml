import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    title: "Simple QML Test"
    width: 400
    height: 300
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        
        Label {
            text: "Simple QML Test Window"
            font.pointSize: 16
            Layout.alignment: Qt.AlignCenter
        }
        
        TextField {
            placeholderText: "Type something..."
            Layout.fillWidth: true
        }
        
        Button {
            text: "Test Button"
            Layout.alignment: Qt.AlignCenter
            
            onClicked: {
                console.log("Button clicked!")
            }
        }
    }
}