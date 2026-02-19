# KDE Tray Icon Double-Click in PyQt6

## Approaches
1. **Built-in Signal**:
```python
self.tray_icon.activated.connect(lambda r: 
    self.on_double_click() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
```

2. **Event Filter**:
```python
class TrayFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.click_count += 1
                if self.click_count == 2:
                    self.handle_double_click()
                    return True
        return False

# Install filter:
self.tray_icon.installEventFilter(TrayFilter(self.tray_icon, self))
```

## Key Notes
- Event filter more reliable across platforms
- Built-in signal simpler but may have limitations
- Test on target KDE environment
- macOS behavior differs (context menus affect detection)