import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    title: "Syllablaze Settings"
    width: 400
    height: 300
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        
        Label {
            text: "Kirigami Settings (Simple Version)"
            font.bold: true
            Layout.alignment: Qt.AlignCenter
        }
        
        Label {
            text: "This is a simplified version for testing"
            Layout.alignment: Qt.AlignCenter
        }
        
        Label {
            text: "Full Kirigami integration coming soon..."
            Layout.alignment: Qt.AlignCenter
        }
    }
}