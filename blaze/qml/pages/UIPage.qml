import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15
import org.kde.kirigami 2.20 as Kirigami

Kirigami.ScrollablePage {
    id: uiPage
    title: "User Interface"

    // ── Listen to setting changes from other sources ──────────────────────
    Connections {
        target: settingsBridge
        function onSettingChanged(key, value) {
            if (key === "popup_style") {
                styleGroup.updateFromValue(value)
            } else if (key === "applet_autohide") {
                autohideSwitch.checked = (value !== false)
            } else if (key === "applet_onalldesktops") {
                onAllDesktopsSwitch.checked = (value !== false)
            } else if (key === "recording_dialog_always_on_top") {
                alwaysOnTopSwitch.checked = (value !== false)
            } else if (key === "progress_window_always_on_top") {
                if (uiPage.currentStyle === "traditional")
                    alwaysOnTopSwitch.checked = (value !== false)
            }
        }
    }

    // ── State ──────────────────────────────────────────────────────────────
    property string currentStyle: "applet"   // drives card highlight + sub-options

    Component.onCompleted: {
        var saved = settingsBridge ? settingsBridge.get("popup_style") : "applet"
        currentStyle = saved || "applet"
    }

    // ── Helper: exclusive card selection ──────────────────────────────────
    QtObject {
        id: styleGroup
        function select(style) {
            uiPage.currentStyle = style
            if (settingsBridge) settingsBridge.set("popup_style", style)
        }
        function updateFromValue(val) {
            uiPage.currentStyle = val || "applet"
        }
    }

    // ── Card component ────────────────────────────────────────────────────
    component StyleCard: Rectangle {
        id: card
        property string styleValue: ""
        property alias previewContent: previewArea.data

        width: 160
        height: 120
        radius: Kirigami.Units.smallSpacing
        color: Kirigami.Theme.backgroundColor
        border.width: uiPage.currentStyle === styleValue ? 2 : 1
        border.color: uiPage.currentStyle === styleValue
                      ? Kirigami.Theme.highlightColor
                      : Kirigami.Theme.disabledTextColor

        // Preview area
        Item {
            id: previewArea
            anchors { top: parent.top; left: parent.left; right: parent.right; bottom: radioRow.top }
            anchors.margins: Kirigami.Units.smallSpacing
            clip: true
        }

        // Radio + label row
        RowLayout {
            id: radioRow
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            QQC2.RadioButton {
                checked: uiPage.currentStyle === card.styleValue
                onClicked: styleGroup.select(card.styleValue)
            }
            QQC2.Label {
                text: card.styleValue.charAt(0).toUpperCase() + card.styleValue.slice(1)
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: styleGroup.select(card.styleValue)
        }
    }

    // ── Main layout ────────────────────────────────────────────────────────
    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.Separator {
            Layout.fillWidth: true
        }
        QQC2.Label {
            text: "Recording Indicator"
            font.bold: true
            font.pointSize: Kirigami.Theme.defaultFont.pointSize + 1
        }

        // ── Three-card grid ────────────────────────────────────────────────
        GridLayout {
            columns: 3
            columnSpacing: Kirigami.Units.largeSpacing
            rowSpacing: 0

            // ── None card ─────────────────────────────────────────────────
            StyleCard {
                styleValue: "none"
                previewContent: [
                    Item {
                        anchors.centerIn: parent
                        width: parent.width
                        height: parent.height
                        QQC2.Label {
                            anchors.centerIn: parent
                            text: "—"
                            font.pointSize: 20
                            opacity: 0.4
                        }
                    }
                ]
            }

            // ── Traditional card ─────────────────────────────────────────
            StyleCard {
                styleValue: "traditional"
                previewContent: [
                    Item {
                        anchors.fill: parent
                        // Mini progress-bar mock
                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 100; height: 10; radius: 5
                                color: Kirigami.Theme.disabledTextColor
                                Rectangle {
                                    width: parent.width * 0.65; height: parent.height; radius: parent.radius
                                    color: Kirigami.Theme.positiveTextColor
                                }
                            }
                            QQC2.Button {
                                text: "Stop"
                                Layout.alignment: Qt.AlignHCenter
                                flat: true
                                enabled: false
                                implicitHeight: 22
                                implicitWidth: 60
                            }
                        }
                    }
                ]
            }

            // ── Applet card ───────────────────────────────────────────────
            StyleCard {
                styleValue: "applet"
                previewContent: [
                    Item {
                        anchors.fill: parent
                        Image {
                            anchors.centerIn: parent
                            width: Math.min(parent.width, parent.height) - 8
                            height: width
                            source: settingsBridge && settingsBridge.svgPath
                                    ? "file://" + settingsBridge.svgPath
                                    : ""
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                        }
                    }
                ]
            }
        }

        // ── Sub-options (conditional) ──────────────────────────────────────
        Kirigami.FormLayout {
            Layout.fillWidth: true
            visible: uiPage.currentStyle === "applet" || uiPage.currentStyle === "traditional"

            // Auto-hide toggle — Applet only
            QQC2.Switch {
                id: autohideSwitch
                Kirigami.FormData.label: "Auto-hide after transcription:"
                visible: uiPage.currentStyle === "applet"
                checked: settingsBridge ? settingsBridge.get("applet_autohide") !== false : true
                onToggled: {
                    if (settingsBridge) settingsBridge.set("applet_autohide", checked)
                }
            }

            // Show on all desktops — Applet + persistent mode only
            QQC2.Switch {
                id: onAllDesktopsSwitch
                Kirigami.FormData.label: "Show on all virtual desktops:"
                visible: uiPage.currentStyle === "applet" && !autohideSwitch.checked
                checked: settingsBridge ? settingsBridge.get("applet_onalldesktops") !== false : true
                onToggled: {
                    if (settingsBridge) settingsBridge.set("applet_onalldesktops", checked)
                }
            }

            // Dialog size — Applet only
            QQC2.SpinBox {
                id: dialogSizeSpinBox
                Kirigami.FormData.label: "Dialog size (px):"
                visible: uiPage.currentStyle === "applet"
                from: 100
                to: 500
                stepSize: 10
                value: settingsBridge ? (settingsBridge.get("recording_dialog_size") || 200) : 200
                onValueModified: {
                    if (settingsBridge) settingsBridge.set("recording_dialog_size", value)
                }
            }

            // Always-on-top — both Applet and Traditional
            QQC2.Switch {
                id: alwaysOnTopSwitch
                Kirigami.FormData.label: uiPage.currentStyle === "applet"
                                         ? "Keep dialog always on top:"
                                         : "Keep window always on top:"
                checked: {
                    if (uiPage.currentStyle === "applet")
                        return settingsBridge ? settingsBridge.get("recording_dialog_always_on_top") !== false : true
                    else
                        return settingsBridge ? settingsBridge.get("progress_window_always_on_top") !== false : true
                }
                onToggled: {
                    if (!settingsBridge) return
                    if (uiPage.currentStyle === "applet")
                        settingsBridge.set("recording_dialog_always_on_top", checked)
                    else
                        settingsBridge.set("progress_window_always_on_top", checked)
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
