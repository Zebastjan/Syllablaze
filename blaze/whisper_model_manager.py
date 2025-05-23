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
                               QMessageBox, QDialog, QProgressBar, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
import re
import logging
import subprocess
import platform
from pathlib import Path
from blaze.settings import Settings
from blaze.constants import DEFAULT_WHISPER_MODEL

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Constants and Utilities
# -------------------------------------------------------------------------

class ModelPaths:
    """Utility class for model path operations"""
    
    @staticmethod
    def get_models_dir():
        """Get the directory where Whisper stores its models"""
        models_dir = os.path.join(Path.home(), ".cache", "whisper")
        os.makedirs(models_dir, exist_ok=True)
        return models_dir
    
    @staticmethod
    def get_faster_whisper_dir(model_name):
        """Get the directory path for a Faster Whisper model"""
        return os.path.join(ModelPaths.get_models_dir(), f"models--Systran--faster-whisper-{model_name}")
    
    @staticmethod
    def get_whisper_file_path(model_name):
        """Get the file path for an original Whisper model"""
        return os.path.join(ModelPaths.get_models_dir(), f"{model_name}.pt")
    
    @staticmethod
    def get_distil_whisper_dir(repo_id):
        """Get the directory path for a Distil Whisper model"""
        return os.path.join(ModelPaths.get_models_dir(), f"models--{repo_id.replace('/', '--')}")

class ModelUtils:
    """Utility class for model operations"""
    
    @staticmethod
    def is_model_downloaded(model_name):
        """Check if a model is downloaded in any format"""
        faster_whisper_dir = ModelPaths.get_faster_whisper_dir(model_name)
        whisper_file_path = ModelPaths.get_whisper_file_path(model_name)
        
        faster_whisper_exists = os.path.exists(faster_whisper_dir)
        whisper_exists = os.path.exists(whisper_file_path)
        
        if faster_whisper_exists:
            logger.info(f"Found Faster Whisper directory for model {model_name}")
        if whisper_exists:
            logger.info(f"Found original Whisper file for model {model_name}")
            
        return faster_whisper_exists or whisper_exists
    
    @staticmethod
    def get_model_path(model_name):
        """Get the best available path for a model"""
        faster_whisper_dir = ModelPaths.get_faster_whisper_dir(model_name)
        whisper_file_path = ModelPaths.get_whisper_file_path(model_name)
        
        if os.path.exists(faster_whisper_dir):
            return faster_whisper_dir
        else:
            return whisper_file_path
    
    @staticmethod
    def calculate_model_size(model_path):
        """Calculate the size of a model in MB"""
        if not os.path.exists(model_path):
            return 0
            
        if os.path.isdir(model_path):
            # For directories, calculate total size of all files
            total_size = 0
            for root, dirs, files in os.walk(model_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            return round(total_size / (1024 * 1024))  # Convert to MB
        elif os.path.isfile(model_path):
            # For files, get the file size
            return round(os.path.getsize(model_path) / (1024 * 1024))  # Convert to MB
        
        return 0
    
    @staticmethod
    def open_directory(path):
        """Open directory in file explorer"""
        if platform.system() == "Windows":
            subprocess.run(['explorer', path])
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(['open', path])
        else:  # Linux
            subprocess.run(['xdg-open', path])

# Define Faster Whisper model information
FASTER_WHISPER_MODELS = {
    # Standard Whisper models
    "tiny": {"size_mb": 75, "description": "Tiny model (75MB)", "type": "standard"},
    "tiny.en": {"size_mb": 75, "description": "Tiny English-only model (75MB)", "type": "standard"},
    "base": {"size_mb": 142, "description": "Base model (142MB)", "type": "standard"},
    "base.en": {"size_mb": 142, "description": "Base English-only model (142MB)", "type": "standard"},
    "small": {"size_mb": 466, "description": "Small model (466MB)", "type": "standard"},
    "small.en": {"size_mb": 466, "description": "Small English-only model (466MB)", "type": "standard"},
    "medium": {"size_mb": 1500, "description": "Medium model (1.5GB)", "type": "standard"},
    "medium.en": {"size_mb": 1500, "description": "Medium English-only model (1.5GB)", "type": "standard"},
    "large-v1": {"size_mb": 2900, "description": "Large v1 model (2.9GB)", "type": "standard"},
    "large-v2": {"size_mb": 3000, "description": "Large v2 model (3.0GB)", "type": "standard"},
    "large-v3": {"size_mb": 3100, "description": "Large v3 model (3.1GB)", "type": "standard"},
    "large-v3-turbo": {"size_mb": 3100, "description": "Large v3 Turbo model - Faster with similar accuracy (3.1GB)", "type": "standard"},
    "large": {"size_mb": 3100, "description": "Large model (3.1GB)", "type": "standard"},
    
    # Distil-Whisper models (optimized for Faster Whisper)
    "distil-medium.en": {"size_mb": 1200, "description": "Distilled Medium English-only model (1.2GB)", "type": "distil", "repo_id": "distil-whisper/distil-medium.en"},
    "distil-large-v2": {"size_mb": 2400, "description": "Distilled Large v2 model (2.4GB)", "type": "distil", "repo_id": "distil-whisper/distil-large-v2"},
    "distil-large-v3": {"size_mb": 2500, "description": "Distilled Large v3 model (2.5GB) - Optimized for Faster Whisper", "type": "distil", "repo_id": "distil-whisper/distil-large-v3"},
    "distil-large-v3.5": {"size_mb": 2500, "description": "Distilled Large v3.5 model (2.5GB) - Latest version", "type": "distil", "repo_id": "distil-whisper/distil-large-v3.5"},
    "distil-small.en": {"size_mb": 400, "description": "Distilled Small English-only model (400MB) - Good for resource-constrained applications", "type": "distil", "repo_id": "distil-whisper/distil-small.en"}
}

# -------------------------------------------------------------------------
# Model Registry
# -------------------------------------------------------------------------

class ModelRegistry:
    """Registry for Whisper model information"""
    
    # Use the existing FASTER_WHISPER_MODELS dictionary
    MODELS = FASTER_WHISPER_MODELS
    
    @classmethod
    def get_model_info(cls, model_name):
        """Get information for a specific model"""
        return cls.MODELS.get(model_name, {})
    
    @classmethod
    def get_all_models(cls):
        """Get list of all available models"""
        return list(cls.MODELS.keys())
    
    @classmethod
    def is_distil_model(cls, model_name):
        """Check if a model is a distil-whisper model"""
        return cls.get_model_info(model_name).get('type') == 'distil'
    
    @classmethod
    def get_repo_id(cls, model_name):
        """Get the repository ID for a model"""
        return cls.get_model_info(model_name).get('repo_id')
    
    @classmethod
    def add_model(cls, model_name, model_info):
        """Add a new model to the registry"""
        cls.MODELS[model_name] = model_info
        logger.info(f"Added new model to registry: {model_name}")
    
    @classmethod
    def update_from_huggingface(cls):
        """Update the registry with models from Hugging Face"""
        try:
            # This would be implemented to query Hugging Face API
            # For now, we'll just use the existing models
            pass
        except Exception as e:
            logger.warning(f"Failed to update model registry from Hugging Face: {e}")

# -------------------------------------------------------------------------
# Model Information Functions
# -------------------------------------------------------------------------

def get_model_info():
    """Get comprehensive information about all Whisper models"""
    # Get the models directory
    models_dir = ModelPaths.get_models_dir()
    
    # Get available models from the registry
    available_models = ModelRegistry.get_all_models()
    logger.info(f"Available models for Faster Whisper: {available_models}")
    
    # Get current active model from settings
    settings = Settings()
    active_model = settings.get('model', DEFAULT_WHISPER_MODEL)
    
    # Scan the directory for all model files
    if os.path.exists(models_dir):
        files_in_cache = os.listdir(models_dir)
        logger.info(f"Files in whisper cache: {files_in_cache}")
    else:
        logger.warning(f"Whisper cache directory does not exist: {models_dir}")
        os.makedirs(models_dir, exist_ok=True)
        files_in_cache = []
    
    # Create model info dictionary
    model_info = {}
    for model_name in available_models:
        # Check if the model is downloaded
        is_downloaded = ModelUtils.is_model_downloaded(model_name)
        
        # Get the model path
        model_path = ModelUtils.get_model_path(model_name)
        
        # Calculate the model size
        actual_size = ModelUtils.calculate_model_size(model_path) if is_downloaded else ModelRegistry.get_model_info(model_name).get('size_mb', 0)
        
        # Get model description
        model_description = ModelRegistry.get_model_info(model_name).get('description', f"{model_name} model")
        
        # Create model info object
        model_info[model_name] = {
            'name': model_name,
            'display_name': model_name.capitalize(),
            'description': model_description,
            'is_downloaded': is_downloaded,
            'size_mb': actual_size,
            'path': model_path,
            'is_active': model_name == active_model
        }
    
    return model_info, models_dir

# -------------------------------------------------------------------------
# Dialog Utilities
# -------------------------------------------------------------------------

class DialogUtils:
    """Utility class for dialog operations"""
    
    @staticmethod
    def confirm_download(model_name, size_mb):
        """Show confirmation dialog before downloading a model"""
        # Get model information from the registry
        model_info = ModelRegistry.get_model_info(model_name)
        if not model_info:
            model_info = {"size_mb": size_mb, "description": f"{model_name} model"}
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(f"Download Faster Whisper model '{model_name}'?")
        msg.setInformativeText(f"This will download approximately {model_info['size_mb']} MB of data.\n{model_info['description']}")
        
        msg.setWindowTitle("Confirm Download")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msg.exec() == QMessageBox.StandardButton.Yes
    
    @staticmethod
    def confirm_delete(model_name, size_mb):
        """Show confirmation dialog before deleting a model"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Delete Faster Whisper model '{model_name}'?")
        msg.setInformativeText(
            f"This will free up {size_mb:.1f} MB of disk space.\n"
            f"You will need to download this model again if you want to use it in the future."
        )
        msg.setWindowTitle("Confirm Deletion")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msg.exec() == QMessageBox.StandardButton.Yes

# For backward compatibility
def confirm_download(model_name, size_mb):
    """Show confirmation dialog before downloading a model (backward compatibility)"""
    return DialogUtils.confirm_download(model_name, size_mb)

def confirm_delete(model_name, size_mb):
    """Show confirmation dialog before deleting a model (backward compatibility)"""
    return DialogUtils.confirm_delete(model_name, size_mb)

def open_directory(path):
    """Open directory in file explorer (backward compatibility)"""
    ModelUtils.open_directory(path)

# -------------------------------------------------------------------------
# Download Components
# -------------------------------------------------------------------------

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
        
        # Current progress values
        self.current_value = 0
        self.max_value = 100
        self.downloaded_mb = 0
        self.total_mb = 0
        
    def set_progress(self, value, maximum):
        """Set progress value"""
        self.current_value = value
        self.max_value = maximum
        self.progress_bar.setValue(value)
        
        # Extract download size from status text if available
        if hasattr(self, 'downloaded_mb') and hasattr(self, 'total_mb') and self.total_mb > 0:
            self.size_label.setText(f"Downloaded: {self.downloaded_mb:.1f} MB / {self.total_mb:.1f} MB")
        
    def set_status(self, text):
        """Update status text and extract size information if available"""
        self.status_label.setText(text)
        
        # Try to extract download size information from status text
        size_match = re.search(r'(\d+\.\d+)MB\s*/\s*(\d+\.\d+)MB', text)
        if size_match:
            self.downloaded_mb = float(size_match.group(1))
            self.total_mb = float(size_match.group(2))
            self.size_label.setText(f"Downloaded: {self.downloaded_mb:.1f} MB / {self.total_mb:.1f} MB")
        
    def set_time_remaining(self, seconds):
        """Update time remaining"""
        if seconds < 0:
            self.time_remaining_label.setText("Estimating time remaining...")
        else:
            minutes, secs = divmod(seconds, 60)
            self.time_remaining_label.setText(f"Time remaining: {int(minutes)}m {int(secs)}s")

class DownloadManager:
    """Manager for model downloads"""
    
    @staticmethod
    def setup_progress_tracking(callback_func):
        """Set up progress tracking for Hugging Face Hub downloads"""
        # Set environment variable to enable progress bar for huggingface_hub
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
        
        try:
            # Try the newer API first
            from huggingface_hub.utils import ProgressCallback
            from huggingface_hub import set_progress_callback
            
            # Create a progress callback adapter
            class HFProgressCallback(ProgressCallback):
                def __call__(self, progress_info):
                    callback_func(progress_info)
            
            # Register the progress callback
            set_progress_callback(HFProgressCallback())
            logger.info("Using newer Hugging Face Hub API for progress tracking")
            return True
        except ImportError:
            # Fall back to older API if available
            try:
                from huggingface_hub import configure_http_backend
                # Try with different parameter names
                try:
                    configure_http_backend(progress_callback=callback_func)
                    logger.info("Using older Hugging Face Hub API for progress tracking (progress_callback)")
                    return True
                except TypeError:
                    # Maybe it uses a different parameter name
                    try:
                        configure_http_backend(callback=callback_func)
                        logger.info("Using older Hugging Face Hub API for progress tracking (callback)")
                        return True
                    except TypeError:
                        logger.warning("Could not configure progress callback for Hugging Face Hub")
            except ImportError:
                logger.warning("Could not import Hugging Face Hub progress tracking API")
        
        return False
    
    @staticmethod
    def download_standard_model(model_name, models_dir):
        """Download a standard Whisper model"""
        from faster_whisper import WhisperModel
        
        logger.info(f"Downloading standard Faster Whisper model: {model_name}")
        return WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            download_root=models_dir,
            local_files_only=False
        )
    
    @staticmethod
    def download_distil_model(repo_id, models_dir):
        """Download a Distil-Whisper model"""
        from faster_whisper import WhisperModel
        
        logger.info(f"Downloading Distil-Whisper model from repo: {repo_id}")
        return WhisperModel(
            repo_id,
            device="cpu",
            compute_type="int8",
            download_root=models_dir,
            local_files_only=False
        )
    
    @staticmethod
    def fallback_download_standard(model_name, models_dir):
        """Fallback method for downloading standard models"""
        try:
            # Try to import the download_model function from faster_whisper.download
            from faster_whisper.download import download_model
            
            # Download the model directly
            download_model(model_name, models_dir)
            logger.info(f"Direct download of model {model_name} completed successfully")
            return True
        except ImportError:
            logger.error("Could not import download_model from faster_whisper.download")
            
            # Try using WhisperModel with a simpler approach
            from faster_whisper import WhisperModel
            WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=models_dir
            )
            logger.info(f"Simple download of model {model_name} completed successfully")
            return True
        
        return False
    
    @staticmethod
    def fallback_download_distil(repo_id, models_dir):
        """Fallback method for downloading distil-whisper models"""
        from huggingface_hub import snapshot_download
        
        # Download the model files
        snapshot_download(
            repo_id=repo_id,
            local_dir=os.path.join(models_dir, f"models--{repo_id.replace('/', '--')}"),
            local_dir_use_symlinks=False
        )
        logger.info(f"Download of distil-whisper model {repo_id} completed successfully")
        return True

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
        self.download_size = 0
        self.downloaded = 0
        self.start_time = 0
        
    def run(self):
        try:
            self.status_update.emit(f"Downloading {self.model_name} model...")
            
            # Import required modules
            import time
            import traceback
            
            # Log the start of the download process
            logger.info(f"Starting download process for model: {self.model_name}")
            
            # Define a progress callback for huggingface_hub
            def progress_callback(progress_info):
                if progress_info.total:
                    # Update total size if we have it
                    self.download_size = progress_info.total
                
                # Update downloaded bytes
                self.downloaded = progress_info.downloaded
                
                # Calculate progress percentage
                if self.download_size > 0:
                    progress_percent = int((self.downloaded / self.download_size) * 100)
                    self.progress_update.emit(progress_percent, 100)
                    
                    # Update status with file size information
                    downloaded_mb = self.downloaded / (1024 * 1024)
                    total_mb = self.download_size / (1024 * 1024)
                    self.status_update.emit(f"Downloading {self.model_name} model... {progress_percent}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)")
                    
                    # Calculate time remaining
                    if self.start_time == 0:
                        self.start_time = time.time()
                    else:
                        elapsed = time.time() - self.start_time
                        if self.downloaded > 0:
                            download_rate = self.downloaded / elapsed  # bytes per second
                            remaining_bytes = self.download_size - self.downloaded
                            if download_rate > 0:
                                time_remaining = remaining_bytes / download_rate
                                self.time_remaining_update.emit(int(time_remaining))
            
            # Set up progress tracking
            DownloadManager.setup_progress_tracking(progress_callback)
            
            # Get model information
            model_info = ModelRegistry.get_model_info(self.model_name)
            model_type = model_info.get('type', 'standard')
            
            # Initialize download
            self.status_update.emit(f"Initializing download of {self.model_name} model...")
            models_dir = ModelPaths.get_models_dir()
            self.start_time = time.time()
            
            # Download based on model type
            try:
                if model_type == 'distil':
                    # For Distil-Whisper models, we need to use the repo_id
                    repo_id = model_info.get('repo_id')
                    if not repo_id:
                        raise ValueError(f"Repository ID not found for Distil-Whisper model '{self.model_name}'")
                    
                    DownloadManager.download_distil_model(repo_id, models_dir)
                else:
                    # For standard models
                    DownloadManager.download_standard_model(self.model_name, models_dir)
                
                # Signal completion
                self.status_update.emit(f"Download of {self.model_name} model completed")
                self.progress_update.emit(100, 100)
                self.download_complete.emit()
                
            except Exception as primary_error:
                # Log the error
                logger.error(f"Primary download method failed: {primary_error}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Try fallback methods
                try:
                    if model_type == 'standard':
                        if DownloadManager.fallback_download_standard(self.model_name, models_dir):
                            self.status_update.emit(f"Download of {self.model_name} model completed")
                            self.progress_update.emit(100, 100)
                            self.download_complete.emit()
                            return
                    else:  # distil model
                        repo_id = model_info.get('repo_id')
                        if repo_id and DownloadManager.fallback_download_distil(repo_id, models_dir):
                            self.status_update.emit(f"Download of {self.model_name} model completed")
                            self.progress_update.emit(100, 100)
                            self.download_complete.emit()
                            return
                    
                    # If we get here, all fallback methods failed
                    raise primary_error
                    
                except Exception as fallback_error:
                    # Log the fallback error
                    logger.error(f"Fallback download failed: {fallback_error}")
                    raise fallback_error
            
        except Exception as e:
            # Handle any errors that occurred during download
            error_msg = f"Error downloading model: {e}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide more detailed error message to the user
            if "Connection error" in str(e):
                self.download_error.emit("Connection error while downloading model. Please check your internet connection and try again.")
            elif "Permission denied" in str(e):
                self.download_error.emit("Permission denied while downloading model. Please check your file permissions.")
            elif "Disk quota exceeded" in str(e):
                self.download_error.emit("Disk quota exceeded. Please free up some disk space and try again.")
            else:
                self.download_error.emit(f"Failed to download model: {str(e)}")

# -------------------------------------------------------------------------
# UI Components
# -------------------------------------------------------------------------

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
        self.table.setHorizontalHeaderLabels([
            "Model", "Use Model", "Size (MB)"
        ])
        
        # Make all columns resize to content for better auto-fitting
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Set the first column (Model name) to stretch to fill remaining space
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.on_table_header_clicked)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Set row height to be closer to text size for more compact display
        self.table.verticalHeader().setDefaultSectionSize(30)
        
        # Make the table take up all available space
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
            if info['is_downloaded'] and os.path.exists(info['path']):
                actually_downloaded.append(name)
        
        # Log detected models for debugging
        logger.info(f"Actually downloaded models: {actually_downloaded}")
        
        self.update_table()
        self.storage_path_label.setText(f"Models stored at: {self.models_dir}")
    
    def update_model_registry(self):
        """Update the model registry with any new models found"""
        try:
            # Import the WhisperModelManager to use its query_huggingface_models method
            from blaze.utils.whisper_model_manager import WhisperModelManager
            model_manager = WhisperModelManager()
            
            # Query available models
            available_models = model_manager.query_huggingface_models()
            
            # Check for new models that aren't in the registry
            for model_name in available_models:
                if model_name.startswith("distil-") and model_name not in ModelRegistry.MODELS:
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
                        "repo_id": repo_id
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
                name_item = QTableWidgetItem(f"⚡ {info['display_name']} ({model_name})")
            else:
                name_item = QTableWidgetItem(f"{info['display_name']} ({model_name})")
                
            if info['is_active']:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
                
            # Add tooltip with description
            if 'description' in info:
                name_item.setToolTip(info['description'])
                
            self.table.setItem(row, 0, name_item)
            
            # Use model button, active indicator, or download button
            use_cell = QWidget()
            use_layout = QHBoxLayout(use_cell)
            use_layout.setContentsMargins(2, 0, 2, 0)  # Reduce vertical margins to make rows more compact
            
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
            # Update settings
            settings = Settings()
            settings.set('model', model_name)
            
            # Emit signal that model was activated
            self.model_activated.emit(model_name)
            
            # Import and use the update_tray_tooltip function
            from blaze.main import update_tray_tooltip
            update_tray_tooltip()
            
            # Refresh the model list to update active status
            self.refresh_model_list()
    
    def on_download_model_clicked(self, model_name):
        """Download the selected model"""
        if model_name not in self.model_info:
            return
            
        info = self.model_info[model_name]
        
        # Confirm download
        if not DialogUtils.confirm_download(model_name, info['size_mb']):
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
        if not DialogUtils.confirm_delete(model_name, info['size_mb']):
            return
            
        # Delete the model file
        try:
            if os.path.isdir(info['path']):
                import shutil
                shutil.rmtree(info['path'])
            else:
                os.remove(info['path'])
                
            self.refresh_model_list()
            self.model_deleted.emit(model_name)
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
                
        ModelUtils.open_directory(self.models_dir)
    
    def on_table_header_clicked(self, sorted_column_index):
        """Sort the table by the clicked column"""
        self.table.sortByColumn(sorted_column_index, Qt.SortOrder.AscendingOrder)