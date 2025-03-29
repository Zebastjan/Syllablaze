# Performance Optimization: File Operations

## 10.5. Inefficient File Operations

**Issue:** The application performs inefficient file operations, particularly when checking for model files.

**Example:**
```python
# In whisper_model_manager.py
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
```

**Solution:** Optimize file operations with caching and batch processing:

```python
# In whisper_model_manager.py
class ModelInfoCache:
    """Cache for model information to reduce file system operations"""
    _cache = {}
    _cache_time = 0
    _cache_lifetime = 60  # seconds
    
    @staticmethod
    def get_model_info():
        """Get model information, using cache when possible"""
        current_time = time.time()
        
        # Check if cache is valid
        if (ModelInfoCache._cache and 
            current_time - ModelInfoCache._cache_time < ModelInfoCache._cache_lifetime):
            return ModelInfoCache._cache.copy(), ModelInfoCache._cache.get('_models_dir', '')
        
        # Cache is invalid or empty, refresh it
        model_info, models_dir = ModelInfoCache._fetch_model_info()
        
        # Update cache
        ModelInfoCache._cache = model_info.copy()
        ModelInfoCache._cache['_models_dir'] = models_dir
        ModelInfoCache._cache_time = current_time
        
        return model_info, models_dir
    
    @staticmethod
    def invalidate_cache():
        """Invalidate the cache"""
        ModelInfoCache._cache = {}
        ModelInfoCache._cache_time = 0
    
    @staticmethod
    def _fetch_model_info():
        """Fetch model information from the file system"""
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
        
        # Check if models directory exists
        if not os.path.exists(models_dir):
            logger.warning(f"Whisper cache directory does not exist: {models_dir}")
            os.makedirs(models_dir, exist_ok=True)
            return {model_name: {
                'name': model_name,
                'display_name': model_name.capitalize(),
                'is_downloaded': False,
                'size_mb': 0,
                'path': os.path.join(models_dir, f"{model_name}.pt"),
                'is_active': model_name == active_model
            } for model_name in available_models}, models_dir
        
        # Get all files in the directory at once
        try:
            dir_files = set(os.listdir(models_dir))
        except Exception as e:
            logger.error(f"Error listing models directory: {e}")
            dir_files = set()
        
        # Create model info dictionary
        model_info = {}
        for model_name in available_models:
            # Check if model file exists
            model_filename = f"{model_name}.pt"
            is_downloaded = model_filename in dir_files
            
            # Get model path
            model_path = os.path.join(models_dir, model_filename)
            
            # Get file size if downloaded
            actual_size = 0
            if is_downloaded:
                try:
                    actual_size = round(os.path.getsize(model_path) / (1024 * 1024))
                except Exception as e:
                    logger.error(f"Error getting size of model file {model_path}: {e}")
            
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

# Replace get_model_info function with cache access
def get_model_info():
    """Get comprehensive information about all Whisper models"""
    return ModelInfoCache.get_model_info()