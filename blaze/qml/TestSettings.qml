import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    visible: true
    title: "Test Settings"
    width: 400
    height: 300
    
    Rectangle {
        anchors.fill: parent
        color: "lightblue"
        
        Text {
            anchors.centerIn: parent
            text: "QML Test Window"
            font.pointSize: 16
        }
    }
}