import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    title: "Test Recording Dialog"
    width: 200
    height: 200
    
    // Circular background
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "#2e3440"
        border.color: "#88c0d0"
        border.width: 2
    }
    
    // Simple content
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 5
        
        Label {
            Layout.alignment: Qt.AlignCenter
            text: "Syllablaze"
            font.pointSize: 12
            color: "white"
        }
        
        Button {
            Layout.alignment: Qt.AlignCenter
            text: "Test"
            
            onClicked: {
                console.log("Test button clicked")
            }
        }
    }
    
    Component.onCompleted: {
        console.log("TestRecordingDialog: Window created")
    }
}