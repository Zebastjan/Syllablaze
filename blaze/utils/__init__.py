"""
Utility modules for Syllablaze
"""

from PyQt6.QtWidgets import QApplication, QWidget

def center_window(window: QWidget):
    """Center a window on the screen"""
    screen = QApplication.primaryScreen().geometry()
    window.move(
        screen.center().x() - window.width() // 2,
        screen.center().y() - window.height() // 2
    )