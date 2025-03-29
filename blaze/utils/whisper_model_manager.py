"""
Whisper Model Manager for Syllablaze

This module provides a high-level interface for managing Whisper models, including:
- Getting information about available models
- Checking if models are downloaded
- Loading models
- Downloading models with progress tracking
- Deleting models
"""

import os
import logging
import threading
from pathlib import Path
from blaze.settings import Settings
from blaze.constants import DEFAULT_WHISPER_MODEL

logger = logging.getLogger(__name__)

class WhisperModelManager:
    """High-level interface for managing Whisper models"""
    
    def __init__(self, settings_service=None):
        self.settings_service = settings_service or Settings()
        self.models_dir = self._get_models_directory()
        
    def _get_models_directory(self):
        """Get the directory where Whisper stores its models"""
        import os
        return os.path.join(Path.home(), ".cache", "whisper")
    
    def get_available_models(self):
        """Get list of all available models"""
        import whisper
        if hasattr(whisper, '_MODELS'):
            return list(whisper._MODELS.keys())
        return []
    
    def get_model_info(self):
        """Get comprehensive information about all models"""
        import os
        
        # Get list of available models
        available_models = self.get_available_models()
        if not available_models:
            logger.error("No available models found")
            return {}, self.models_dir
        
        # Get current active model from settings
        active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
        
        # Ensure models directory exists
        if not os.path.exists(self.models_dir):
            logger.warning(f"Whisper cache directory does not exist: {self.models_dir}")
            os.makedirs(self.models_dir, exist_ok=True)
        
        # Create model info dictionary
        model_info = {}
        for model_name in available_models:
            model_info[model_name] = self.get_single_model_info(model_name, active_model)
        
        return model_info, self.models_dir
    
    def get_single_model_info(self, model_name, active_model=None):
        """Get information about a single model"""
        import os
        
        if active_model is None:
            active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
            
        model_path = os.path.join(self.models_dir, f"{model_name}.pt")
        is_downloaded = os.path.exists(model_path)
        actual_size = 0
        
        if is_downloaded:
            actual_size = round(os.path.getsize(model_path) / (1024 * 1024))
            
        return {
            'name': model_name,
            'display_name': model_name.capitalize(),
            'is_downloaded': is_downloaded,
            'size_mb': actual_size,
            'path': model_path,
            'is_active': model_name == active_model
        }
    
    def get_model_path(self, model_name):
        """Get the file path for a specific model"""
        import os
        return os.path.join(self.models_dir, f"{model_name}.pt")
    
    def is_model_downloaded(self, model_name):
        """Check if a model is downloaded"""
        model_path = self.get_model_path(model_name)
        return os.path.exists(model_path)
    
    def load_model(self, model_name):
        """Load a Whisper model"""
        import whisper
        import logging as whisper_logging
        
        # Check if model is downloaded
        if not self.is_model_downloaded(model_name):
            error_msg = f"Model '{model_name}' is not downloaded"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Redirect whisper's logging to our logger
        whisper_logging.getLogger("whisper").setLevel(logging.WARNING)
            
        # Load the model
        logger.info(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name)
        logger.info(f"Model '{model_name}' loaded successfully")
        
        return model
    
    def download_model(self, model_name, progress_callback=None):
        """Download a model with progress updates"""
        import whisper
        
        # Define a download function for the thread
        def download_thread_func():
            try:
                # Whisper's load_model will download if not present
                whisper.load_model(model_name)
                if progress_callback:
                    progress_callback(100, "Download complete")
            except Exception as e:
                logger.error(f"Error downloading model: {e}")
                if progress_callback:
                    progress_callback(-1, f"Error: {str(e)}")
        
        # Start download in a separate thread
        thread = threading.Thread(target=download_thread_func)
        thread.daemon = True
        thread.start()
        
        return thread
    
    def delete_model(self, model_name):
        """Delete a model file"""
        import os
        
        # Check if model is active
        active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
        if model_name == active_model:
            raise ValueError("Cannot delete the currently active model")
            
        model_path = self.get_model_path(model_name)
        if os.path.exists(model_path):
            os.remove(model_path)
            logger.info(f"Deleted model: {model_name}")
            return True
        
        logger.warning(f"Model file not found: {model_path}")
        return False