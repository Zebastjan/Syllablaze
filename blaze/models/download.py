"""
Model download functionality for Whisper models
"""

import os
import logging
from PyQt6.QtCore import QThread, pyqtSignal

from blaze.models.registry import ModelRegistry
from blaze.models.paths import ModelPaths

logger = logging.getLogger(__name__)


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
                    logger.info(
                        "Using older Hugging Face Hub API for progress tracking (progress_callback)"
                    )
                    return True
                except TypeError:
                    # Maybe it uses a different parameter name
                    try:
                        configure_http_backend(callback=callback_func)
                        logger.info(
                            "Using older Hugging Face Hub API for progress tracking (callback)"
                        )
                        return True
                    except TypeError:
                        logger.warning(
                            "Could not configure progress callback for Hugging Face Hub"
                        )
            except ImportError:
                logger.warning(
                    "Could not import Hugging Face Hub progress tracking API"
                )

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
            local_files_only=False,
        )

    @staticmethod
    def download_distil_model(repo_id, models_dir):
        """Download a Distil-Whisper model using snapshot_download.

        WhisperModel() tries to both download AND load the model with CTranslate2,
        which fails for repos that use safetensors format (no model.bin).
        snapshot_download just downloads files without trying to load them.
        """
        from huggingface_hub import snapshot_download

        logger.info(f"Downloading Distil-Whisper model from repo: {repo_id}")
        snapshot_download(
            repo_id=repo_id,
            local_dir=os.path.join(models_dir, f"models--{repo_id.replace('/', '--')}"),
            local_dir_use_symlinks=False,
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
                model_name, device="cpu", compute_type="int8", download_root=models_dir
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
            local_dir_use_symlinks=False,
        )
        logger.info(
            f"Download of distil-whisper model {repo_id} completed successfully"
        )
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
                    self.status_update.emit(
                        f"Downloading {self.model_name} model... {progress_percent}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)"
                    )

                    # Calculate time remaining
                    if self.start_time == 0:
                        self.start_time = time.time()
                    else:
                        elapsed = time.time() - self.start_time
                        if self.downloaded > 0:
                            download_rate = (
                                self.downloaded / elapsed
                            )  # bytes per second
                            remaining_bytes = self.download_size - self.downloaded
                            if download_rate > 0:
                                time_remaining = remaining_bytes / download_rate
                                self.time_remaining_update.emit(int(time_remaining))

            # Set up progress tracking
            DownloadManager.setup_progress_tracking(progress_callback)

            # Get model information
            model_info = ModelRegistry.get_model_info(self.model_name)
            model_type = model_info.get("type", "standard")

            # Initialize download
            self.status_update.emit(
                f"Initializing download of {self.model_name} model..."
            )
            models_dir = ModelPaths.get_models_dir()
            self.start_time = time.time()

            # Download based on model type
            try:
                if model_type == "distil":
                    # For Distil-Whisper models, we need to use the repo_id
                    repo_id = model_info.get("repo_id")
                    if not repo_id:
                        raise ValueError(
                            f"Repository ID not found for Distil-Whisper model '{self.model_name}'"
                        )

                    DownloadManager.download_distil_model(repo_id, models_dir)
                else:
                    # For standard models
                    DownloadManager.download_standard_model(self.model_name, models_dir)

                # Signal completion
                self.status_update.emit(
                    f"Download of {self.model_name} model completed"
                )
                self.progress_update.emit(100, 100)
                self.download_complete.emit()

            except Exception as primary_error:
                # Log the error
                logger.error(f"Primary download method failed: {primary_error}")
                logger.error(f"Traceback: {traceback.format_exc()}")

                # Try fallback methods
                try:
                    if model_type == "standard":
                        if DownloadManager.fallback_download_standard(
                            self.model_name, models_dir
                        ):
                            self.status_update.emit(
                                f"Download of {self.model_name} model completed"
                            )
                            self.progress_update.emit(100, 100)
                            self.download_complete.emit()
                            return
                    else:  # distil model
                        repo_id = model_info.get("repo_id")
                        if repo_id and DownloadManager.fallback_download_distil(
                            repo_id, models_dir
                        ):
                            self.status_update.emit(
                                f"Download of {self.model_name} model completed"
                            )
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
                self.download_error.emit(
                    "Connection error while downloading model. Please check your internet connection and try again."
                )
            elif "Permission denied" in str(e):
                self.download_error.emit(
                    "Permission denied while downloading model. Please check your file permissions."
                )
            elif "Disk quota exceeded" in str(e):
                self.download_error.emit(
                    "Disk quota exceeded. Please free up some disk space and try again."
                )
            else:
                self.download_error.emit(f"Failed to download model: {str(e)}")
