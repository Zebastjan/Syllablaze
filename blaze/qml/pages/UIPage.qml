import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15
import org.kde.kirigami 2.20 as Kirigami

Kirigami.ScrollablePage {
    id: uiPage
    title: "User Interface"

    // Listen to setting changes from other sources (e.g., dialog dismissal)
    Connections {
        target: settingsBridge
        function onSettingChanged(key, value) {
            if (key === "show_recording_dialog") {
                showDialogSwitch.checked = (value !== false)
            } else if (key === "show_progress_window") {
                showProgressSwitch.checked = (value !== false)
            } else if (key === "recording_dialog_always_on_top") {
                alwaysOnTopSwitch.checked = (value !== false)
            } else if (key === "progress_window_always_on_top") {
                progressAlwaysOnTopSwitch.checked = (value !== false)
            } else if (key === "applet_mode") {
                var modeIndex = appletModeCombo.indexOfValue(value)
                if (modeIndex >= 0) appletModeCombo.currentIndex = modeIndex
            }
        }
    }

    // Applet mode options model
    property var appletModes: [
        { value: "popup",      label: "Popup — show on record, hide after" },
        { value: "persistent", label: "Persistent — always visible"        },
        { value: "off",        label: "Off — never shown automatically"    },
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        // Recording Dialog Section
        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: "Recording Dialog"
            }

            QQC2.ComboBox {
                id: appletModeCombo
                Kirigami.FormData.label: "Dialog mode:"
                model: appletModes.map(function(m) { return m.label })

                // Helper: find index by value string
                function indexOfValue(val) {
                    for (var i = 0; i < appletModes.length; i++) {
                        if (appletModes[i].value === val) return i
                    }
                    return 0
                }

                Component.onCompleted: {
                    var savedMode = settingsBridge ? settingsBridge.get("applet_mode") : "popup"
                    currentIndex = indexOfValue(savedMode || "popup")
                }

                onActivated: {
                    if (settingsBridge) {
                        settingsBridge.set("applet_mode", appletModes[currentIndex].value)
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Popup: dialog appears when recording starts and hides after transcription. " +
                      "Persistent: dialog stays visible. Off: dialog never shown automatically."
                wrapMode: Text.WordWrap
                opacity: 0.7
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            QQC2.Switch {
                id: showDialogSwitch
                Kirigami.FormData.label: "Show recording dialog:"
                checked: settingsBridge ? settingsBridge.get("show_recording_dialog") !== false : true
                onToggled: {
                    if (settingsBridge) {
                        settingsBridge.set("show_recording_dialog", checked)
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Display a circular floating dialog that shows recording status and volume visualization"
                wrapMode: Text.WordWrap
                opacity: 0.7
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            QQC2.SpinBox {
                id: dialogSizeSpinBox
                Kirigami.FormData.label: "Dialog size (px):"
                from: 100
                to: 500
                stepSize: 10
                value: settingsBridge ? (settingsBridge.get("recording_dialog_size") || 200) : 200
                enabled: showDialogSwitch.checked
                onValueModified: {
                    if (settingsBridge) {
                        settingsBridge.set("recording_dialog_size", value)
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Size of the circular recording indicator (100-500 pixels)"
                wrapMode: Text.WordWrap
                opacity: 0.7
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            QQC2.Switch {
                id: alwaysOnTopSwitch
                Kirigami.FormData.label: "Keep dialog always on top:"
                checked: settingsBridge ? settingsBridge.get("recording_dialog_always_on_top") !== false : true
                enabled: showDialogSwitch.checked
                onToggled: {
                    if (settingsBridge) {
                        settingsBridge.set("recording_dialog_always_on_top", checked)
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Recording dialog will always stay above other windows for quick access"
                wrapMode: Text.WordWrap
                opacity: 0.7
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }
        }

        // Progress Window Section
        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: "Progress Window"
            }

            QQC2.Switch {
                id: showProgressSwitch
                Kirigami.FormData.label: "Show progress window:"
                checked: settingsBridge ? settingsBridge.get("show_progress_window") !== false : true
                onToggled: {
                    if (settingsBridge) {
                        settingsBridge.set("show_progress_window", checked)
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Show the traditional progress window during recording and transcription"
                wrapMode: Text.WordWrap
                opacity: 0.7
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            QQC2.Switch {
                id: progressAlwaysOnTopSwitch
                Kirigami.FormData.label: "Keep progress window always on top:"
                checked: settingsBridge ? settingsBridge.get("progress_window_always_on_top") !== false : true
                enabled: showProgressSwitch.checked
                onToggled: {
                    if (settingsBridge) {
                        settingsBridge.set("progress_window_always_on_top", checked)
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: "Progress window will stay above other windows (for testing always-on-top functionality)"
                wrapMode: Text.WordWrap
                opacity: 0.7
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
