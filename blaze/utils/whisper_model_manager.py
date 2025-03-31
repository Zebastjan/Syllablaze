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
from blaze.constants import (
    DEFAULT_WHISPER_MODEL, DEFAULT_COMPUTE_TYPE, DEFAULT_DEVICE
)

logger = logging.getLogger(__name__)

class WhisperModelManager:
    """High-level interface for managing Whisper models"""
    
    # Define available models for Faster Whisper
    AVAILABLE_MODELS = [
        "tiny", "tiny.en",
        "base", "base.en",
        "small", "small.en",
        "medium", "medium.en",
        "large-v1", "large-v2", "large-v3", "large"
    ]
    
    def __init__(self, settings_service=None):
        self.settings_service = settings_service or Settings()
        self.models_dir = self._get_models_directory()
        
        # Configure huggingface to use the whisper cache directory
        os.environ["HF_HOME"] = self.models_dir
        
    def _get_models_directory(self):
        """Get the directory where Whisper stores its models"""
        
        # Use only the whisper directory
        whisper_dir = os.path.join(Path.home(), ".cache", "whisper")
        
        # Ensure the directory exists
        os.makedirs(whisper_dir, exist_ok=True)
        
        return whisper_dir
    
    def get_model_path(self, model_name):
        """Get the file path for a specific model"""
        
        # For Faster Whisper, models are stored in a directory structure like:
        # models--Systran--faster-whisper-{model_name}
        faster_whisper_model_dir = os.path.join(
            self.models_dir,
            f"models--Systran--faster-whisper-{model_name}"
        )
        
        # Check if the Faster Whisper model directory exists
        if os.path.exists(faster_whisper_model_dir):
            return faster_whisper_model_dir
        
        # Fall back to the original Whisper .pt file path
        # This is for backward compatibility
        return os.path.join(self.models_dir, f"{model_name}.pt")
    
    def get_available_models(self):
        """Get list of all available models"""
        return self.AVAILABLE_MODELS
    
    def get_model_info(self):
        """Get comprehensive information about all models"""
        
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
        
        if active_model is None:
            active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
            
        # Check if the model is downloaded
        is_downloaded = self.is_model_downloaded(model_name)
        
        # Get the model path
        model_path = self.get_model_path(model_name)
        
        # Calculate the model size
        actual_size = 0
        
        if is_downloaded:
            # If it's a directory (Faster Whisper format), calculate total size of all files
            if os.path.isdir(model_path):
                for root, dirs, files in os.walk(model_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            actual_size += os.path.getsize(file_path)
                actual_size = round(actual_size / (1024 * 1024))  # Convert to MB
            # If it's a file (original Whisper format), get its size
            elif os.path.isfile(model_path):
                actual_size = round(os.path.getsize(model_path) / (1024 * 1024))
            
        # Import model information from the main module
        try:
            from blaze.whisper_model_manager import FASTER_WHISPER_MODELS
            model_info = FASTER_WHISPER_MODELS.get(model_name, {})
        except ImportError:
            # If we can't import, use default values
            model_info = {}
        
        # Use the size from FASTER_WHISPER_MODELS if available and the model is not downloaded
        if actual_size == 0 and 'size_mb' in model_info:
            actual_size = model_info.get('size_mb', 0)
            
        return {
            'name': model_name,
            'display_name': model_name.capitalize(),
            'description': model_info.get('description', f"{model_name} model"),
            'is_downloaded': is_downloaded,
            'size_mb': actual_size,
            'path': model_path,
            'is_active': model_name == active_model,
            'type': model_info.get('type', 'standard')
        }
    
    def is_model_downloaded(self, model_name):
        """Check if a model is downloaded"""
        import os
        
        # Check for Faster Whisper model directory (Hugging Face format)
        # Format is typically: models--Systran--faster-whisper-{model_name}
        faster_whisper_model_dir = os.path.join(
            self.models_dir,
            f"models--Systran--faster-whisper-{model_name}"
        )
        
        # Check for original Whisper .pt file (for backward compatibility)
        whisper_model_path = os.path.join(self.models_dir, f"{model_name}.pt")
        
        # Log what we're checking for
        logger.info(f"Checking for model {model_name} in:")
        logger.info(f"  - Faster Whisper directory: {faster_whisper_model_dir}")
        logger.info(f"  - Original Whisper file: {whisper_model_path}")
        
        # Check if either format exists
        faster_whisper_exists = os.path.exists(faster_whisper_model_dir)
        whisper_exists = os.path.exists(whisper_model_path)
        
        if faster_whisper_exists:
            logger.info(f"Found Faster Whisper directory for model {model_name}")
        if whisper_exists:
            logger.info(f"Found original Whisper file for model {model_name}")
        
        # Check if either format exists
        return faster_whisper_exists or whisper_exists
    
    def load_model(self, model_name):
        """Load a Whisper model using Faster Whisper"""
        # Check if hf_transfer is available using importlib
        try:
            import importlib.util
            if importlib.util.find_spec("hf_transfer") is not None:
                # If it's available, we can use it
                os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
                logger.info("Using hf_transfer for faster downloads")
            else:
                # If it's not available, disable it to avoid errors
                os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
                logger.info("hf_transfer not available, using standard download method")
        except ImportError:
            # If importlib.util is not available, disable hf_transfer
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
            logger.info("Could not check for hf_transfer, using standard download method")
            
        # Import Faster Whisper
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.error("Failed to import faster_whisper. Please install it with: pip install faster-whisper>=1.1.0")
            raise ImportError("faster_whisper is not installed. Please install it with: pip install faster-whisper>=1.1.0")
        
        # Get compute type and device from settings
        compute_type = self.settings_service.get('compute_type', DEFAULT_COMPUTE_TYPE)
        device = self.settings_service.get('device', DEFAULT_DEVICE)
        
        # Map compute types to Faster Whisper format
        compute_type_map = {
            'float32': 'float32',
            'float16': 'float16',
            'int8': 'int8'
        }
        
        # For GPU with mixed precision
        if device == 'cuda' and compute_type == 'float16':
            ct = 'float16'
        # For GPU with int8 quantization
        elif device == 'cuda' and compute_type == 'int8':
            ct = 'int8_float16'
        # For CPU
        else:
            ct = compute_type_map.get(compute_type, 'float32')
        
        # Get the models directory
        models_dir = self._get_models_directory()
        
        # Check if the model is already downloaded in either format
        is_downloaded = self.is_model_downloaded(model_name)
        
        # Try to import model information
        try:
            from blaze.whisper_model_manager import FASTER_WHISPER_MODELS
            # Check if this is a Distil-Whisper model
            model_info = FASTER_WHISPER_MODELS.get(model_name, {})
            model_type = model_info.get('type', 'standard')
        except ImportError:
            # If we can't import, assume it's a standard model
            model_info = {}
            model_type = 'standard'
        
        logger.info(f"Loading model: {model_name} (type: {model_type}, device: {device}, compute_type: {ct})")
        
        try:
            # Try to use CTranslate2 model catalog for loading if available
            try:
                import ctranslate2
                # Check if the model exists in the CTranslate2 catalog
                if hasattr(ctranslate2.models, 'Whisper') and hasattr(ctranslate2.models.Whisper, 'get_model_path'):
                    # Try to get the model path from the catalog
                    model_path = ctranslate2.models.Whisper.get_model_path(model_name, models_dir)
                    if model_path and os.path.exists(model_path):
                        logger.info(f"Using CTranslate2 model from path: {model_path}")
                        model = WhisperModel(model_path, device=device, compute_type=ct)
                        return model
            except (ImportError, AttributeError) as e:
                logger.warning(f"CTranslate2 model catalog not available or doesn't support this model: {e}")
                
            # If CTranslate2 catalog approach didn't work, use the standard approach
            if model_type == 'distil':
                # For Distil-Whisper models, we need to use the repo_id
                repo_id = model_info.get('repo_id')
                if not repo_id:
                    error_msg = f"Repository ID not found for Distil-Whisper model '{model_name}'"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
                logger.info(f"Loading Distil-Whisper model: {model_name} (repo_id: {repo_id})")
                model = WhisperModel(
                    repo_id,
                    device=device,
                    compute_type=ct,
                    download_root=models_dir,
                    local_files_only=is_downloaded  # Only use local files if already downloaded
                )
            else:
                # For standard models, allow automatic downloading from Hugging Face Hub
                logger.info(f"Loading standard model: {model_name}")
                model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=ct,
                    download_root=models_dir,
                    local_files_only=False  # Allow downloading from Hugging Face Hub
                )
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            # If there was an error and the model isn't downloaded, try to download it
            if not is_downloaded:
                logger.info(f"Model {model_name} not found locally, attempting to download...")
                try:
                    model = WhisperModel(
                        model_name,
                        device=device,
                        compute_type=ct,
                        download_root=models_dir,
                        local_files_only=False
                    )
                except Exception as download_error:
                    logger.error(f"Failed to download model: {download_error}")
                    raise ValueError(f"Failed to download model '{model_name}': {download_error}")
            else:
                # If the model is downloaded but still fails to load, raise the original error
                raise
            
        logger.info(f"Model '{model_name}' loaded successfully")
        return model
    
    def download_model(self, model_name, progress_callback=None):
        """Download a model with progress updates"""
        # Define a download function for the thread
        def download_thread_func():
            try:
                # Check if hf_transfer is available using importlib
                try:
                    import importlib.util
                    if importlib.util.find_spec("hf_transfer") is not None:
                        # If it's available, we can use it
                        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
                        logger.info("Using hf_transfer for faster downloads")
                    else:
                        # If it's not available, disable it to avoid errors
                        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
                        logger.info("hf_transfer not available, using standard download method")
                except ImportError:
                    # If importlib.util is not available, disable hf_transfer
                    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
                    logger.info("Could not check for hf_transfer, using standard download method")
                
                # Get the models directory
                models_dir = self._get_models_directory()
                
                if progress_callback:
                    progress_callback(10, f"Starting download of {model_name} model...")
                
                # Try to use CTranslate2 model catalog for downloading
                try:
                    import ctranslate2
                    logger.info(f"Using CTranslate2 model catalog to download {model_name}")
                    
                    if progress_callback:
                        progress_callback(20, f"Downloading {model_name} using CTranslate2 model catalog...")
                    
                    # Download the model using CTranslate2 model catalog
                    model_path = ctranslate2.models.Whisper.download(
                        model_name=model_name,
                        saving_directory=models_dir
                    )
                    
                    logger.info(f"Model downloaded successfully to: {model_path}")
                    
                    if progress_callback:
                        progress_callback(90, "Model downloaded successfully, finalizing...")
                        
                except (ImportError, AttributeError) as e:
                    # If CTranslate2 model catalog is not available or doesn't support this model,
                    # fall back to Faster Whisper's built-in download mechanism
                    logger.warning(f"CTranslate2 model catalog not available or doesn't support this model: {e}")
                    logger.info("Falling back to Faster Whisper's built-in download mechanism")
                    
                    if progress_callback:
                        progress_callback(20, "Falling back to Faster Whisper's built-in download mechanism...")
                    
                    # Import Faster Whisper
                    from faster_whisper import WhisperModel
                    
                    # Try to import model information
                    try:
                        from blaze.whisper_model_manager import FASTER_WHISPER_MODELS
                        # Check if this is a Distil-Whisper model
                        model_info = FASTER_WHISPER_MODELS.get(model_name, {})
                        model_type = model_info.get('type', 'standard')
                    except ImportError:
                        # If we can't import, assume it's a standard model
                        model_info = {}
                        model_type = 'standard'
                    
                    if model_type == 'distil':
                        # For Distil-Whisper models, we need to use the repo_id
                        repo_id = model_info.get('repo_id')
                        if not repo_id:
                            error_msg = f"Repository ID not found for Distil-Whisper model '{model_name}'"
                            logger.error(error_msg)
                            if progress_callback:
                                progress_callback(-1, f"Error: {error_msg}")
                            return
                            
                        logger.info(f"Downloading Distil-Whisper model: {model_name} (repo_id: {repo_id})")
                        WhisperModel(repo_id, device="cpu", compute_type="int8", download_root=models_dir)
                    else:
                        # For standard models, use the Hugging Face Hub automatic downloading
                        logger.info(f"Downloading model: {model_name} from Hugging Face Hub")
                        WhisperModel(model_name, device="cpu", compute_type="int8", download_root=models_dir)
                
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