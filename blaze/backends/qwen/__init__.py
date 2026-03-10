"""
Qwen Backend

Speech-to-text using Alibaba's Qwen2.5-Omni multimodal models via llama-mtmd-cli.

Dependencies:
    - llama-mtmd-cli binary (from llama.cpp)
    - huggingface-hub (for model downloads)

Models (GGUF quantized):
    7B Series:
    - qwen2.5-omni-7b-q4: 4.8GB, 6-8GB RAM, GPU preferred
    - qwen2.5-omni-7b-q6: 6.4GB, 8-10GB RAM, GPU preferred
    - qwen2.5-omni-7b-q8: 8.2GB, 10-12GB RAM, GPU preferred

    3B Series (lower hardware requirements):
    - qwen2.5-omni-3b-q4: 2.5GB, 4-6GB RAM, CPU preferred
    - qwen2.5-omni-3b-q6: 2.9GB, 5-7GB RAM, CPU preferred
    - qwen2.5-omni-3b-q8: 3.7GB, 6-8GB RAM, CPU preferred

Supported languages:
    - 10,000+ languages including Chinese, English, Japanese, Korean,
      Arabic, French, German, Spanish, Italian, Portuguese, Russian, and many more
"""

# Check dependencies
try:
    import huggingface_hub
except ImportError as e:
    raise ImportError(
        f"Qwen backend requires huggingface-hub: {e}. "
        "Install with: pip install huggingface-hub"
    )

from blaze.backends.qwen.backend import QwenBackend

__all__ = ["QwenBackend"]
