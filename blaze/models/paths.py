"""
Model path utilities for Whisper models
"""

import os
import logging
import subprocess
import platform
from pathlib import Path

logger = logging.getLogger(__name__)


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
        return os.path.join(
            ModelPaths.get_models_dir(), f"models--Systran--faster-whisper-{model_name}"
        )

    @staticmethod
    def get_whisper_file_path(model_name):
        """Get the file path for an original Whisper model"""
        return os.path.join(ModelPaths.get_models_dir(), f"{model_name}.pt")

    @staticmethod
    def get_distil_whisper_dir(repo_id):
        """Get the directory path for a Distil Whisper model (Systran's CTranslate2 versions)"""
        return os.path.join(
            ModelPaths.get_models_dir(), f"models--{repo_id.replace('/', '--')}"
        )

    @staticmethod
    def get_faster_distil_dir(model_name):
        """Get the directory path for Systran's faster-distil-whisper models

        Note: Systran repos are named 'faster-distil-whisper-medium.en' (no 'distil-' prefix)
        but our model_name is 'distil-medium.en', so we strip the 'distil-' prefix
        """
        # Strip 'distil-' prefix from model name for Systran repo path
        # distil-medium.en -> medium.en
        suffix = (
            model_name.replace("distil-", "", 1)
            if model_name.startswith("distil-")
            else model_name
        )
        return os.path.join(
            ModelPaths.get_models_dir(),
            f"models--Systran--faster-distil-whisper-{suffix}",
        )


class ModelUtils:
    """Utility class for model operations"""

    @staticmethod
    def is_model_downloaded(model_name):
        """Check if a model is downloaded in any format"""
        faster_whisper_dir = ModelPaths.get_faster_whisper_dir(model_name)
        whisper_file_path = ModelPaths.get_whisper_file_path(model_name)

        faster_whisper_exists = os.path.exists(faster_whisper_dir)
        whisper_exists = os.path.exists(whisper_file_path)

        # Check for Systran's CTranslate2-converted distil-whisper models
        faster_distil_dir = ModelPaths.get_faster_distil_dir(model_name)
        faster_distil_exists = os.path.exists(faster_distil_dir)

        if faster_whisper_exists:
            logger.info(f"Found Faster Whisper directory for model {model_name}")
        if whisper_exists:
            logger.info(f"Found original Whisper file for model {model_name}")
        if faster_distil_exists:
            logger.info(f"Found Faster Distil-Whisper directory for model {model_name}")

        return faster_whisper_exists or whisper_exists or faster_distil_exists

    @staticmethod
    def get_model_path(model_name):
        """Get the best available path for a model"""
        faster_whisper_dir = ModelPaths.get_faster_whisper_dir(model_name)
        whisper_file_path = ModelPaths.get_whisper_file_path(model_name)
        faster_distil_dir = ModelPaths.get_faster_distil_dir(model_name)

        if os.path.exists(faster_whisper_dir):
            return faster_whisper_dir
        elif os.path.exists(faster_distil_dir):
            return faster_distil_dir
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
            subprocess.run(["explorer", path])
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
