# Performance Optimization: Settings Access

## 10.4. Inefficient Settings Access

**Issue:** The application frequently accesses settings, which can involve disk I/O and slow down operations.

**Example:**
```python
# In various places
settings = Settings()
model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
language_code = settings.get('language', 'auto')

# In update_tooltip method
def update_tooltip(self, recognized_text=None):
    """Update the tooltip with app name, version, model and language information"""
    import sys
    
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    language_code = settings.get('language', 'auto')
    
    # ...
```

**Solution:** Implement settings caching and batch updates:

```python
# In settings.py
class Settings:
    # Class-level cache
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the settings object"""
        self.settings = QSettings(APP_NAME, APP_NAME)
        self._load_cache()
        
    def _load_cache(self):
        """Load all settings into cache"""
        # Load common settings into cache
        common_keys = ['model', 'language', 'mic_index', 'sample_rate_mode']
        for key in common_keys:
            default = self._get_default(key)
            value = self.settings.value(key, default)
            # Validate and store in cache
            Settings._cache[key] = self._validate(key, value, default)
    
    def _get_default(self, key):
        """Get default value for a key"""
        if key == 'model':
            return DEFAULT_WHISPER_MODEL
        elif key == 'language':
            return 'auto'
        elif key == 'sample_rate_mode':
            return DEFAULT_SAMPLE_RATE_MODE
        return None
    
    def _validate(self, key, value, default):
        """Validate a setting value"""
        # Existing validation logic...
        return value
    
    def get(self, key, default=None):
        """Get a setting value, using cache when possible"""
        # Check cache first
        if key in Settings._cache:
            return Settings._cache[key]
        
        # Not in cache, get from QSettings
        value = self.settings.value(key, default)
        
        # Validate and cache the value
        validated_value = self._validate(key, value, default)
        Settings._cache[key] = validated_value
        
        return validated_value
    
    def set(self, key, value):
        """Set a setting value and update cache"""
        # Validate before saving
        validated_value = self._validate(key, value, self._get_default(key))
        
        # Update QSettings
        self.settings.setValue(key, validated_value)
        
        # Update cache
        Settings._cache[key] = validated_value
        
        # Sync to disk
        self.settings.sync()
        
    def clear_cache(self):
        """Clear the settings cache"""
        Settings._cache.clear()
        self._load_cache()