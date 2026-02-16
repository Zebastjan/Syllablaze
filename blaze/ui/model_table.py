"""
Whisper model management table widget
"""

import os
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QHeaderView,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from blaze.models.registry import ModelRegistry
from blaze.models.paths import ModelUtils
from blaze.models.manager import get_model_info
from blaze.models.download import ModelDownloadThread
from blaze.ui.dialogs import DialogUtils, ModelDownloadDialog

logger = logging.getLogger(__name__)


class WhisperModelTableWidget(QWidget):
    """Widget for displaying and managing Whisper models"""

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
        """Set up the UI components"""
        layout = QVBoxLayout(self)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Model", "Use Model", "Size (MB)"])

        # Make all columns resize to content for better auto-fitting
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        # Set the first column (Model name) to stretch to fill remaining space
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(
            self.on_table_header_clicked
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Set row height to be closer to text size for more compact display
        self.table.verticalHeader().setDefaultSectionSize(30)

        # Make the table take up all available space
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addWidget(self.table)

        # Create storage path display with label on one line and button on the next
        storage_layout = QVBoxLayout()

        # Path label
        self.storage_path_label = QLabel()
        storage_layout.addWidget(self.storage_path_label)

        # Button in its own layout to control width
        button_layout = QHBoxLayout()
        self.open_storage_button = QPushButton("Open Directory")
        # Set a fixed width for the button to make it not too wide
        self.open_storage_button.setFixedWidth(120)
        self.open_storage_button.clicked.connect(self.on_open_storage_clicked)
        button_layout.addWidget(self.open_storage_button)
        button_layout.addStretch()  # Push button to the left

        storage_layout.addLayout(button_layout)
        layout.addLayout(storage_layout)

    def refresh_model_list(self):
        """Refresh the model list and update the table"""
        # First, try to update the model registry with any new models
        self.update_model_registry()

        # Then get the model info
        self.model_info, self.models_dir = get_model_info()

        # Log which models are actually downloaded
        actually_downloaded = []
        for name, info in self.model_info.items():
            if info["is_downloaded"] and os.path.exists(info["path"]):
                actually_downloaded.append(name)

        # Log detected models for debugging
        logger.info(f"Actually downloaded models: {actually_downloaded}")

        self.update_table()
        self.storage_path_label.setText(f"Models stored at: {self.models_dir}")

    def update_model_registry(self):
        """Update the model registry with any new models found"""
        try:
            # Import the WhisperModelManager to use its query_huggingface_models method
            from blaze.models.manager import WhisperModelManager

            model_manager = WhisperModelManager()

            # Query available models
            available_models = model_manager.query_huggingface_models()

            # Check for new models that aren't in the registry
            for model_name in available_models:
                if (
                    model_name.startswith("distil-")
                    and model_name not in ModelRegistry.MODELS
                ):
                    # This is a new distil-whisper model, add it to the registry
                    logger.info(f"Found new distil-whisper model: {model_name}")

                    # Determine size based on model name
                    if "small" in model_name:
                        size_mb = 400
                    elif "medium" in model_name:
                        size_mb = 1200
                    elif "large" in model_name:
                        size_mb = 2500
                    else:
                        size_mb = 1000  # Default size

                    # Create repo_id based on model name
                    repo_id = f"distil-whisper/{model_name}"

                    # Add to registry
                    model_info = {
                        "size_mb": size_mb,
                        "description": f"Distilled {model_name.replace('distil-', '').capitalize()} model ({size_mb}MB)",
                        "type": "distil",
                        "repo_id": repo_id,
                    }
                    ModelRegistry.add_model(model_name, model_info)

        except Exception as e:
            logger.warning(f"Failed to update model registry: {e}")

    def update_table(self):
        """Update the table with current model information"""
        self.table.setRowCount(0)  # Clear table

        for model_name, info in self.model_info.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Model name with special formatting for Distil-Whisper models
            is_distil = ModelRegistry.is_distil_model(model_name)
            if is_distil:
                name_item = QTableWidgetItem(
                    f"⚡ {info['display_name']} ({model_name})"
                )
            else:
                name_item = QTableWidgetItem(f"{info['display_name']} ({model_name})")

            if info["is_active"]:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)

            # Add tooltip with description
            if "description" in info:
                name_item.setToolTip(info["description"])

            self.table.setItem(row, 0, name_item)

            # Use model button, active indicator, or download button
            use_cell = QWidget()
            use_layout = QHBoxLayout(use_cell)
            use_layout.setContentsMargins(
                2, 0, 2, 0
            )  # Reduce vertical margins to make rows more compact

            if info["is_downloaded"]:
                if info["is_active"]:
                    # Show green check mark for active model
                    active_label = QLabel("✓ Active")
                    active_label.setStyleSheet("color: green; font-weight: bold;")
                    use_layout.addWidget(active_label)
                else:
                    # Show "Use Model" button for downloaded but inactive models
                    use_button = QPushButton("Use Model")
                    use_button.clicked.connect(
                        lambda _, m=model_name: self.on_use_model_clicked(m)
                    )
                    use_layout.addWidget(use_button)
            else:
                # Show "Download" button for models that aren't downloaded
                download_button = QPushButton("Download")
                download_button.clicked.connect(
                    lambda _, m=model_name: self.on_download_model_clicked(m)
                )
                use_layout.addWidget(download_button)

            self.table.setCellWidget(row, 1, use_cell)

            # Size
            size_item = QTableWidgetItem(f"{int(info['size_mb'])}")
            size_item.setData(
                Qt.ItemDataRole.DisplayRole, info["size_mb"]
            )  # For sorting
            self.table.setItem(row, 2, size_item)

    def on_use_model_clicked(self, model_name):
        """Set the selected model as active"""
        if (
            model_name in self.model_info
            and self.model_info[model_name]["is_downloaded"]
        ):
            # Emit signal — the connected handler (SettingsWindow.on_model_activated)
            # handles settings write, transcriber update, and tooltip update.
            self.model_activated.emit(model_name)

            # Refresh the model list to update active status
            self.refresh_model_list()

    def on_download_model_clicked(self, model_name):
        """Download the selected model"""
        if model_name not in self.model_info:
            return

        info = self.model_info[model_name]

        # Confirm download
        if not DialogUtils.confirm_download(model_name, info["size_mb"]):
            return

        # Create and show download dialog
        download_dialog = ModelDownloadDialog(model_name, self)
        download_dialog.show()

        # Start download in a separate thread
        self.download_thread = ModelDownloadThread(model_name)
        self.download_thread.progress_update.connect(download_dialog.set_progress)
        self.download_thread.status_update.connect(download_dialog.set_status)
        self.download_thread.time_remaining_update.connect(
            download_dialog.set_time_remaining
        )
        self.download_thread.download_complete.connect(
            lambda: self.handle_download_complete(model_name, download_dialog)
        )
        self.download_thread.download_error.connect(
            lambda error: self.handle_download_error(error, download_dialog)
        )
        self.download_thread.start()

    def handle_download_complete(self, model_name, dialog):
        """Handle successful model download"""
        dialog.close()
        self.refresh_model_list()
        self.model_downloaded.emit(model_name)

    def handle_download_error(self, error, dialog):
        """Handle model download error"""
        dialog.close()
        QMessageBox.critical(
            self, "Download Error", f"Failed to download model: {error}"
        )

    def on_delete_model_clicked(self, model_name):
        """Delete the selected model"""
        if model_name not in self.model_info:
            return

        info = self.model_info[model_name]

        # Cannot delete active model
        if info["is_active"]:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete the currently active model. Please select a different model first.",
            )
            return

        # Confirm deletion
        if not DialogUtils.confirm_delete(model_name, info["size_mb"]):
            return

        # Delete the model file
        try:
            if os.path.isdir(info["path"]):
                import shutil

                shutil.rmtree(info["path"])
            else:
                os.remove(info["path"])

            self.refresh_model_list()
            self.model_deleted.emit(model_name)
        except Exception as e:
            QMessageBox.critical(
                self, "Deletion Error", f"Failed to delete model: {str(e)}"
            )

    def on_open_storage_clicked(self):
        """Open the model storage directory in file explorer"""
        if not os.path.exists(self.models_dir):
            try:
                os.makedirs(self.models_dir)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to create models directory: {str(e)}"
                )
                return

        ModelUtils.open_directory(self.models_dir)

    def on_table_header_clicked(self, sorted_column_index):
        """Sort the table by the clicked column"""
        self.table.sortByColumn(sorted_column_index, Qt.SortOrder.AscendingOrder)
