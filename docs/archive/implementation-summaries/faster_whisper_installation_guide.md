# Faster Whisper Installation Guide

## Overview

This document outlines the necessary modifications to Syllablaze's installation and uninstallation processes to support Faster Whisper. These changes ensure that all required dependencies are properly installed and configured.

## Installation Modifications

### Requirements.txt Updates

The `requirements.txt` file needs to be updated to include Faster Whisper:

```
# Add Faster Whisper
faster-whisper>=1.1.0
```

### Setup.py Updates

The `setup.py` file needs to be modified to include Faster Whisper in the installation requirements:

```python
install_requires=[
    # Existing requirements
    'PyQt6>=6.0.0',
    'numpy>=1.20.0',
    'scipy>=1.7.0',
    'pyaudio>=0.2.11',
    'keyboard',
    'psutil',
    
    # Add Faster Whisper
    'faster-whisper>=1.1.0',
],
```

### Install.py Modifications

The `install.py` script should be updated to check for GPU support and install the appropriate dependencies:

```python
# Add to install.py

def check_gpu_support():
    """Check if CUDA is available for GPU acceleration"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
    except Exception:
        return False

# In the main installation function
has_gpu = check_gpu_support()
if has_gpu:
    print("GPU support detected. Installing CUDA dependencies...")
    # Inform user about CUDA requirements
    print("Note: For optimal performance with Faster Whisper on GPU, ensure you have:")
    print("- CUDA 12 with cuBLAS")
    print("- cuDNN 9 for CUDA 12")
    print("These can be installed separately if not already present.")
else:
    print("No GPU detected. Configuring for CPU-only operation.")
```

### Additional Dependencies for GPU Support

For users with NVIDIA GPUs, additional instructions should be provided:

```
# For GPU support, the following additional packages are recommended:
# pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*
```

## Uninstallation Modifications

The `uninstall.py` script should be updated to clean up any Faster Whisper specific files:

```python
# Add to uninstall.py

def cleanup_faster_whisper():
    """Clean up Faster Whisper specific files"""
    # Faster Whisper uses the same cache directory as original Whisper
    # No additional cleanup needed for model files
    
    print("Cleaning up Faster Whisper...")
    
    # Remove any Faster Whisper specific settings
    try:
        from blaze.settings import Settings
        settings = Settings()
        
        # Remove Faster Whisper specific settings
        faster_whisper_settings = [
            'compute_type',
            'device',
            'beam_size',
            'vad_filter',
            'word_timestamps'
        ]
        
        for setting in faster_whisper_settings:
            if setting in settings.settings:
                del settings.settings[setting]
                
        settings.save()
        print("Faster Whisper settings removed.")
    except Exception as e:
        print(f"Error cleaning up Faster Whisper settings: {e}")

# Call this function in the main uninstallation process
cleanup_faster_whisper()
```

## First-Run Configuration

When Syllablaze is first run after updating to Faster Whisper, it should detect the available hardware and configure optimal settings:

```python
# Add to main.py or settings.py

def configure_faster_whisper():
    """Configure optimal settings for Faster Whisper based on hardware"""
    settings = Settings()
    
    # Check if this is the first run with Faster Whisper settings
    if 'compute_type' not in settings.settings:
        # Check for GPU support
        try:
            import torch
            has_gpu = torch.cuda.is_available()
        except ImportError:
            has_gpu = False
        except Exception:
            has_gpu = False
            
        if has_gpu:
            # Configure for GPU
            settings.set('device', 'cuda')
            settings.set('compute_type', 'float16')  # Good balance of speed and accuracy
        else:
            # Configure for CPU
            settings.set('device', 'cpu')
            settings.set('compute_type', 'int8')  # Best performance on CPU
            
        # Set other defaults
        settings.set('beam_size', 5)
        settings.set('vad_filter', True)
        settings.set('word_timestamps', False)
        
        print("Faster Whisper configured with optimal settings for your hardware.")
```

## Troubleshooting

Include common troubleshooting steps for installation issues:

1. **GPU Support Issues**:
   - Ensure CUDA toolkit is properly installed
   - Check that cuDNN is installed and compatible with your CUDA version
   - Verify GPU drivers are up to date

2. **Import Errors**:
   - If you encounter `ImportError` for Faster Whisper, try reinstalling with:
     ```
     pip uninstall -y faster-whisper
     pip install faster-whisper
     ```

3. **Performance Issues**:
   - For CPU: Try setting `compute_type` to 'int8' for better performance
   - For GPU: Try setting `compute_type` to 'float16' or 'int8_float16'
   - Adjust `batch_size` based on available memory

## Conclusion

These modifications to the installation and uninstallation processes will ensure a smooth implementation of Faster Whisper. The automatic configuration based on hardware detection will provide optimal performance for all users.