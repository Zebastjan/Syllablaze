import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    
    property real volumeLevel: 0.0
    property bool isRecording: false
    
    radius: width / 2
    color: "transparent"
    border.color: "gray"
    border.width: 1
    
    // Volume indicator (simple circle that grows)
    Rectangle {
        id: volumeIndicator
        anchors.centerIn: parent
        width: Math.max(10, parent.width * 0.8 * volumeLevel)
        height: Math.max(10, parent.height * 0.8 * volumeLevel)
        radius: width / 2
        color: root.isRecording ? "red" : "blue"
        
        Behavior on width {
            NumberAnimation { duration: 100 }
        }
        
        Behavior on height {
            NumberAnimation { duration: 100 }
        }
    }
    
    // Volume level text
    Label {
        anchors.centerIn: parent
        text: Math.round(volumeLevel * 100) + "%"
        font.pointSize: 8
        color: "white"
        visible: volumeLevel > 0.1
    }
}