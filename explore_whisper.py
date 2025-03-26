import whisper
import os
import sys

def main():
    print("Exploring Whisper model loading...")
    
    # Check if _MODELS exists
    if hasattr(whisper, '_MODELS'):
        print("\nWhisper _MODELS dictionary:")
        for model_name, model_obj in whisper._MODELS.items():
            print(f"  - {model_name}: {type(model_obj).__name__}")
    else:
        print("whisper._MODELS not found")
    
    # Check available models
    print("\nWhisper available models:")
    for model_name in whisper.available_models():
        print(f"  - {model_name}")
    
    # Check model cache directory
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    print(f"\nWhisper cache directory: {cache_dir}")
    if os.path.exists(cache_dir):
        print("Files in cache directory:")
        for file in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, file)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"  - {file} ({size_mb:.1f} MB)")
    else:
        print("Cache directory not found")
    
    # Check if we can get model info without downloading
    print("\nTrying to get model info without downloading:")
    try:
        # Try to access model info without downloading
        for model_name in whisper.available_models():
            model_path = whisper._download(model_name, False)
            print(f"  - {model_name}: {model_path}")
    except Exception as e:
        print(f"Error accessing model info: {e}")

if __name__ == "__main__":
    main()