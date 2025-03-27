# Double-Click Detection for KDE Tray Icons in PyQt6

This document outlines the approaches for implementing double-click detection for system tray icons in KDE using PyQt6.

## Overview

KDE tray icons can have double-click detection when implemented with PyQt6. There are two main approaches to implement this functionality:

1. Using the built-in `activated` signal with `ActivationReason.DoubleClick`
2. Using event filters to handle mouse events directly

## Approach 1: Using the built-in activated signal

QSystemTrayIcon provides an `activated` signal that includes an `ActivationReason` parameter which can be `QSystemTrayIcon.ActivationReason.DoubleClick`. This is the simplest approach:

```python
import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget
from PyQt6.QtGui import QIcon

class SystemTrayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Create the tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set the icon
        self.tray_icon.setIcon(QIcon.fromTheme("application-x-executable"))
        
        # Create the context menu
        self.tray_menu = QMenu()
        self.exit_action = self.tray_menu.addAction("Exit")
        self.exit_action.triggered.connect(self.close_application)
        
        # Set the context menu
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # Connect the activated signal to our custom slot
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show the tray icon
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        # Check the activation reason
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Handle double-click event
            print("Tray icon was double-clicked!")
            self.on_double_click()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Handle single-click event
            print("Tray icon was single-clicked!")
    
    def on_double_click(self):
        # Implement your double-click action here
        # For example, show the main window
        self.show()
        self.activateWindow()
    
    def close_application(self):
        # Clean up and exit
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    
    # Make sure the application doesn't exit when the main window is closed
    app.setQuitOnLastWindowClosed(False)
    
    # Create and set up the application
    tray_app = SystemTrayApp()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

## Approach 2: Using Event Filters

According to feedback from Qt developers, a more reliable approach is to use event filters to handle mouse events directly. This is especially useful if you need more control over the double-click behavior:

```python
import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QObject, QEvent, Qt, QTimer

class SystemTrayFilter(QObject):
    def __init__(self, tray_icon, parent=None):
        super().__init__(parent)
        self.tray_icon = tray_icon
        self.last_click_time = 0
        self.click_count = 0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.reset_click_count)
        
    def eventFilter(self, obj, event):
        if obj == self.tray_icon:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.click_count += 1
                    if self.click_count == 1:
                        # Start timer to detect double click
                        self.timer.start(QApplication.instance().doubleClickInterval())
                    elif self.click_count == 2:
                        # Double click detected
                        self.timer.stop()
                        self.handle_double_click()
                        self.reset_click_count()
                        return True
        return False
    
    def reset_click_count(self):
        self.click_count = 0
    
    def handle_double_click(self):
        # Handle the double-click event
        print("Double-click detected through event filter!")
        if self.parent():
            self.parent().on_double_click()

class SystemTrayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Create the tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set the icon
        self.tray_icon.setIcon(QIcon.fromTheme("application-x-executable"))
        
        # Create the context menu
        self.tray_menu = QMenu()
        self.exit_action = self.tray_menu.addAction("Exit")
        self.exit_action.triggered.connect(self.close_application)
        
        # Set the context menu
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # Install event filter
        self.tray_filter = SystemTrayFilter(self.tray_icon, self)
        self.tray_icon.installEventFilter(self.tray_filter)
        
        # Show the tray icon
        self.tray_icon.show()
    
    def on_double_click(self):
        # Implement your double-click action here
        # For example, show the main window
        self.show()
        self.activateWindow()
    
    def close_application(self):
        # Clean up and exit
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    
    # Make sure the application doesn't exit when the main window is closed
    app.setQuitOnLastWindowClosed(False)
    
    # Create and set up the application
    tray_app = SystemTrayApp()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

## Important Considerations

1. **Platform-Specific Behavior**:
   - The Qt documentation notes that on macOS, a double-click will only be emitted if no context menu is set, since the menu opens on mouse press
   - This shouldn't affect KDE, but it's good to be aware of platform differences

2. **Event Filter Approach Benefits**:
   - More reliable across platforms
   - Gives you more control over the double-click behavior
   - Allows you to implement custom timing and behavior

3. **Potential Issues**:
   - According to user feedback, the event filter approach may not work on macOS
   - The activated signal approach is simpler but may have limitations in some environments

4. **Testing**:
   - Always test your implementation on the target KDE environment
   - Different KDE versions might have slight variations in behavior

## References

- [Qt Documentation for QSystemTrayIcon](https://doc.qt.io/qt-6/qsystemtrayicon.html)
- [Qt Documentation for Event Filters](https://doc.qt.io/qt-6/eventsandfilters.html)
- [Qt Documentation for QMouseEvent](https://doc.qt.io/qt-6/qmouseevent.html)