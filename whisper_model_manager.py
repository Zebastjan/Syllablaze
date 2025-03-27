"""
Whisper Model Manager for Syllablaze

This module provides components for managing Whisper models, including:
- Checking which models are downloaded
- Downloading models with progress tracking
- Deleting models
- Setting active models
- Displaying model information
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView,
                             QMessageBox, QDialog, QProgressBar, QSizePolicy,
                             QApplication, QSystemTrayIcon)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
import os
import logging
import time
import random
from pathlib import Path
from settings import Settings
from constants import DEFAULT_WHISPER_MODEL

logger = logging.getLogger(__name__)

def get_model_info():
    """Get comprehensive information about all Whisper models"""
    import whisper
    import os
    from pathlib import Path
    
    # Get the directory where Whisper stores its models
    models_dir = os.path.join(Path.home(), ".cache", "whisper")
    
    # Get list of available models from Whisper
    available_models = []
    if hasattr(whisper, '_MODELS'):
        available_models = list(whisper._MODELS.keys())
        logger.info(f"Available models in whisper._MODELS: {available_models}")
    else:
        logger.error("whisper._MODELS not found")
        return {}, models_dir
    
    # Get current active model from settings
    settings = Settings()
    active_model = settings.get('model', DEFAULT_WHISPER_MODEL)
    
    # Scan the directory for all model files
    if os.path.exists(models_dir):
        logger.info(f"Files in whisper cache: {os.listdir(models_dir)}")
    else:
        logger.warning(f"Whisper cache directory does not exist: {models_dir}")
        os.makedirs(models_dir, exist_ok=True)
    
    # Create model info dictionary
    model_info = {}
    for model_name in available_models:
        # Check for exact match only (model_name.pt)
        model_path = os.path.join(models_dir, f"{model_name}.pt")
        is_downloaded = os.path.exists(model_path)
        actual_size = 0
        
        # If model file exists, get its size
        if is_downloaded:
            actual_size = round(os.path.getsize(model_path) / (1024 * 1024))  # Convert to MB and round to integer
            logger.info(f"Found model {model_name} at {model_path}")
        
        # Create model info object
        model_info[model_name] = {
            'name': model_name,
            'display_name': model_name.capitalize(),
            'is_downloaded': is_downloaded,
            'size_mb': actual_size,
            'path': model_path,
            'is_active': model_name == active_model
        }
    
    return model_info, models_dir

def confirm_download(model_name, size_mb):
    """Show confirmation dialog before downloading a model"""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setText(f"Download Whisper model '{model_name}'?")
    msg.setInformativeText(
        f"This will download approximately {size_mb:.1f} MB of data."
    )
    msg.setWindowTitle("Confirm Download")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return msg.exec() == QMessageBox.StandardButton.Yes

def confirm_delete(model_name, size_mb):
    """Show confirmation dialog before deleting a model"""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setText(f"Delete Whisper model '{model_name}'?")
    msg.setInformativeText(
        f"This will free up approximately {size_mb:.1f} MB of disk space.\n"
        f"You will need to download this model again if you want to use it in the future."
    )
    msg.setWindowTitle("Confirm Deletion")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return msg.exec() == QMessageBox.StandardButton.Yes

def open_directory(path):
    """Open directory in file explorer"""
    import subprocess
    import platform
    
    if platform.system() == "Windows":
        subprocess.run(['explorer', path])
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(['open', path])
    else:  # Linux
        subprocess.run(['xdg-open', path])

class ModelDownloadDialog(QDialog):
    """Dialog to show model download progress"""
    def __init__(self, model_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Downloading {model_name} model")
        self.setFixedSize(400, 180)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | 
                          Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowSystemMenuHint)
        
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel(f"Preparing to download {model_name} model...")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Size label
        self.size_label = QLabel("Downloaded: 0 MB / 0 MB")
        layout.addWidget(self.size_label)
        
        # Time remaining label
        self.time_remaining_label = QLabel("Estimating time remaining...")
        layout.addWidget(self.time_remaining_label)
        
        # Update timer for smooth progress updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # Update every 100ms
        
        # Current progress values
        self.current_value = 0
        self.target_value = 0
        self.max_value = 100
        
    def set_progress(self, value, maximum):
        """Set target progress value"""
        self.target_value = value
        self.max_value = maximum
        
    def set_status(self, text):
        """Update status text"""
        self.status_label.setText(text)
        
    def set_time_remaining(self, seconds):
        """Update time remaining"""
        if seconds < 0:
            self.time_remaining_label.setText("Estimating time remaining...")
        else:
            minutes, secs = divmod(seconds, 60)
            self.time_remaining_label.setText(f"Time remaining: {int(minutes)}m {int(secs)}s")
            
    def update_display(self):
        """Smoothly update the progress bar"""
        if self.current_value < self.target_value:
            self.current_value = min(self.current_value + 1, self.target_value)
            self.progress_bar.setValue(int(self.current_value))
            
            # Update size label
            if self.max_value > 0:
                downloaded = (self.current_value / self.max_value) * 100
                total = 100
                self.size_label.setText(f"Downloaded: {downloaded:.1f} MB / {total:.1f} MB")

class ModelDownloadThread(QThread):
    """Thread for downloading Whisper models"""
    progress_update = pyqtSignal(int, int)  # value, maximum
    status_update = pyqtSignal(str)
    time_remaining_update = pyqtSignal(int)  # seconds
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    
    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name
        
    def run(self):
        try:
            self.status_update.emit(f"Downloading {self.model_name} model...")
            
            # Since whisper.load_model() handles downloading automatically,
            # we need to simulate progress updates
            import time
            import whisper
            import random
            
            # Get model info for size estimate
            model_info, _ = get_model_info()
            estimated_size = model_info[self.model_name]['size_mb']
            
            # Simulate download progress
            total_steps = 100
            for i in range(total_steps):
                # Simulate network speed variations
                time.sleep(0.1 + random.random() * 0.1)
                
                # Update progress
                self.progress_update.emit(i, total_steps)
                
                # Update status periodically
                if i % 10 == 0:
                    self.status_update.emit(f"Downloading {self.model_name} model... {i}%")
                
                # Update time remaining
                remaining_steps = total_steps - i
                time_per_step = 0.15  # average time per step in seconds
                time_remaining = remaining_steps * time_per_step
                self.time_remaining_update.emit(int(time_remaining))
            
            # Actually download the model
            self.status_update.emit(f"Finalizing download of {self.model_name} model...")
            whisper.load_model(self.model_name)
            
            self.download_complete.emit()
            
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            self.download_error.emit(str(e))

class WhisperModelTable(QWidget):
    model_activated = pyqtSignal(str)  # Emitted when a model is set as active
    model_downloaded = pyqtSignal(str)  # Emitted when a model is downloaded
    model_deleted = pyqtSignal(str)  # Emitted when a model is deleted
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_info = {}
        self.models_dir = ""
        self.setup_ui()
        self.refresh_model_list()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create refresh button
        refresh_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Model List")
        self.refresh_button.clicked.connect(self.refresh_model_list)
        refresh_layout.addWidget(self.refresh_button)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Model", "Use Model", "Size (MB)"
        ])
        
        # Set column resize mode to stretch to fill available space
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Make specific columns resize to content
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Model name
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Use Model
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Size
        
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.on_table_header_clicked)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Set row height to be comfortable
        self.table.verticalHeader().setDefaultSectionSize(60)
        
        # Make the table take up most of the available space
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.table)
        
        # Create storage path display
        storage_layout = QHBoxLayout()
        self.storage_path_label = QLabel()
        storage_layout.addWidget(self.storage_path_label)
        self.open_storage_button = QPushButton("Open")
        self.open_storage_button.clicked.connect(self.on_open_storage_clicked)
        storage_layout.addWidget(self.open_storage_button)
        layout.addLayout(storage_layout)
    
    def refresh_model_list(self):
        """Refresh the model list and update the table"""
        self.model_info, self.models_dir = get_model_info()
        
        # Log which models are actually downloaded
        actually_downloaded = []
        for name, info in self.model_info.items():
            if info['is_downloaded'] and os.path.exists(info['path']):
                actually_downloaded.append(name)
        
        # Log detected models for debugging
        logger.info(f"Actually downloaded models: {actually_downloaded}")
        
        self.update_table()
        self.storage_path_label.setText(f"Models stored at: {self.models_dir}")
    
    def update_table(self):
        """Update the table with current model information"""
        self.table.setRowCount(0)  # Clear table
        
        for model_name, info in self.model_info.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Model name
            name_item = QTableWidgetItem(f"{info['display_name']} ({model_name})")
            if info['is_active']:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
            self.table.setItem(row, 0, name_item)
            
            # Use model button, active indicator, or download button
            use_cell = QWidget()
            use_layout = QHBoxLayout(use_cell)
            use_layout.setContentsMargins(3, 3, 3, 3)
            
            if info['is_downloaded']:
                if info['is_active']:
                    # Show green check mark for active model
                    active_label = QLabel("✓ Active")
                    active_label.setStyleSheet("color: green; font-weight: bold;")
                    use_layout.addWidget(active_label)
                else:
                    # Show "Use Model" button for downloaded but inactive models
                    use_button = QPushButton("Use Model")
                    use_button.clicked.connect(lambda _, m=model_name: self.on_use_model_clicked(m))
                    use_layout.addWidget(use_button)
            else:
                # Show "Download" button for models that aren't downloaded
                download_button = QPushButton("Download")
                download_button.clicked.connect(lambda _, m=model_name: self.on_download_model_clicked(m))
                use_layout.addWidget(download_button)
            
            self.table.setCellWidget(row, 1, use_cell)
            
            # Size
            size_item = QTableWidgetItem(f"{int(info['size_mb'])}")
            size_item.setData(Qt.ItemDataRole.DisplayRole, info['size_mb'])  # For sorting
            self.table.setItem(row, 2, size_item)
    
    def on_use_model_clicked(self, model_name):
        """Set the selected model as active"""
        if model_name in self.model_info and self.model_info[model_name]['is_downloaded']:
            # Update is_active status
            for name in self.model_info:
                self.model_info[name]['is_active'] = (name == model_name)
            
            # Emit signal that model was activated
            self.model_activated.emit(model_name)
            
            # Force immediate tooltip update in main application
            app = QApplication.instance()
            if app:
                # Find all tray icons and update their tooltips
                for widget in app.topLevelWidgets():
                    # Check if this widget is a QSystemTrayIcon
                    if isinstance(widget, QSystemTrayIcon) and hasattr(widget, 'update_tooltip'):
                        widget.update_tooltip()
                    
                    # Also search through all child widgets recursively
                    tray_icons = widget.findChildren(QSystemTrayIcon)
                    for tray_icon in tray_icons:
                        if hasattr(tray_icon, 'update_tooltip'):
                            tray_icon.update_tooltip()
            
            # Update the table display
            self.update_table()
    
    def on_download_model_clicked(self, model_name):
        """Download the selected model"""
        if model_name not in self.model_info:
            return
            
        info = self.model_info[model_name]
        
        # Confirm download
        if not confirm_download(model_name, info['size_mb']):
            return
            
        # Create and show download dialog
        download_dialog = ModelDownloadDialog(model_name, self)
        download_dialog.show()
        
        # Start download in a separate thread
        self.download_thread = ModelDownloadThread(model_name)
        self.download_thread.progress_update.connect(download_dialog.set_progress)
        self.download_thread.status_update.connect(download_dialog.set_status)
        self.download_thread.time_remaining_update.connect(download_dialog.set_time_remaining)
        self.download_thread.download_complete.connect(lambda: self.handle_download_complete(model_name, download_dialog))
        self.download_thread.download_error.connect(lambda error: self.handle_download_error(error, download_dialog))
        self.download_thread.start()
    
    def handle_download_complete(self, model_name, dialog):
        """Handle successful model download"""
        dialog.close()
        self.refresh_model_list()
        self.model_downloaded.emit(model_name)
        QMessageBox.information(self, "Download Complete", 
                              f"Whisper model '{model_name}' has been downloaded successfully.")
    
    def handle_download_error(self, error, dialog):
        """Handle model download error"""
        dialog.close()
        QMessageBox.critical(self, "Download Error", 
                           f"Failed to download model: {error}")
    
    def on_delete_model_clicked(self, model_name):
        """Delete the selected model"""
        if model_name not in self.model_info:
            return
            
        info = self.model_info[model_name]
        
        # Cannot delete active model
        if info['is_active']:
            QMessageBox.warning(self, "Cannot Delete", 
                              "Cannot delete the currently active model. Please select a different model first.")
            return
            
        # Confirm deletion
        if not confirm_delete(model_name, info['size_mb']):
            return
            
        # Delete the model file
        try:
            os.remove(info['path'])
            self.refresh_model_list()
            self.model_deleted.emit(model_name)
            QMessageBox.information(self, "Model Deleted", 
                                  f"Whisper model '{model_name}' has been deleted successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Deletion Error", 
                               f"Failed to delete model: {str(e)}")
    
    def on_open_storage_clicked(self):
        """Open the model storage directory in file explorer"""
        if not os.path.exists(self.models_dir):
            try:
                os.makedirs(self.models_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                                   f"Failed to create models directory: {str(e)}")
                return
                
        open_directory(self.models_dir)
    
    def on_table_header_clicked(self, column_index):
        """Sort the table by the clicked column"""
        self.table.sortByColumn(column_index, Qt.SortOrder.AscendingOrder)