# Faster Whisper Installation with pipx

This guide provides instructions for installing and uninstalling Syllablaze with Faster Whisper using pipx.

## Installation

Syllablaze uses pipx for installation, which creates an isolated environment for the application and its dependencies. This ensures that Syllablaze doesn't interfere with other Python applications on your system.

### Prerequisites

Before installing, ensure you have the following dependencies:

1. Python 3.8 or higher
2. pipx
3. ffmpeg

On Ubuntu/Debian:
```bash
sudo apt install python3-pipx ffmpeg
```

On Fedora:
```bash
sudo dnf install pipx ffmpeg
```

### Installation Steps

1. Clone the repository or download the source code:
   ```bash
   git clone https://github.com/PabloVitasso/Syllablaze.git
   cd Syllablaze
   ```

2. Run the installation script:
   ```bash
   python install.py
   ```

   The installation script will:
   - Check for required system dependencies
   - Install Syllablaze and its dependencies using pipx
   - Install desktop integration files for KDE
   - Verify the installation

3. After installation, you can run Syllablaze in two ways:
   - Type `syllablaze` in the terminal
   - Find it in your application menu under 'Utilities' or 'AudioVideo'

### First Run

On first run, Syllablaze will:
1. Detect your hardware capabilities
2. Configure optimal Faster Whisper settings based on your hardware
3. Download the selected Whisper model if it's not already downloaded

## Uninstallation

To uninstall Syllablaze:

1. Run the uninstallation script:
   ```bash
   python uninstall.py
   ```

   The uninstallation script will:
   - Remove the pipx installation
   - Remove desktop integration files
   - Preserve Whisper models in ~/.cache/whisper (compatible with both OpenAI Whisper and Faster Whisper)

2. If you want to remove the Whisper models as well:
   ```bash
   rm -rf ~/.cache/whisper
   ```

## Manual Installation/Uninstallation with pipx

If you prefer to use pipx commands directly:

### Installation
```bash
# Install with pipx
pipx install .
```

### Uninstallation
```bash
# Uninstall with pipx
pipx uninstall syllablaze
```

## Troubleshooting

### Missing Dependencies
If you encounter errors about missing dependencies, install them manually:
```bash
pip install faster-whisper pyaudio keyboard
```

### GPU Support
For GPU acceleration with Faster Whisper, ensure you have:
- CUDA 12 with cuBLAS
- cuDNN 9 for CUDA 12

These can be installed with:
```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*
```

### Model Download Issues
If you encounter issues downloading models:
1. Check your internet connection
2. Ensure you have sufficient disk space
3. Try downloading the model manually by running Syllablaze and selecting the model in the settings

### Application Not Found in Menu
If the application doesn't appear in your KDE menu after installation:
1. Log out and log back in
2. Or run `kbuildsycoca5` (or `kbuildsycoca6` for newer KDE versions) to refresh the menu cache