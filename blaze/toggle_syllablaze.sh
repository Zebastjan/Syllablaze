#!/bin/bash
#  In KDE Plasma 6, this must be input as an application rather than a command in order for it to function properly.
gdbus call --session --dest org.kde.syllablaze --object-path /org/kde/syllablaze --method org.kde.Syllablaze.ToggleRecording
