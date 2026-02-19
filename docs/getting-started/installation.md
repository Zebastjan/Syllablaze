# Installation Guide

This guide walks you through installing Syllablaze on your Linux system.

## Prerequisites

Syllablaze requires:
- **Python 3.8+**
- **pipx** (user-level package installer)
- **portaudio** (audio input/output library)
- **KDE Plasma** (recommended) - works on other DEs with reduced features

## Step 1: Install System Dependencies

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev python3-pipx
```

### Fedora

```bash
sudo dnf install -y python3-libs python3-devel python3 portaudio-devel pipx
```

### Arch Linux

```bash
sudo pacman -S python python-pip portaudio python-pipx
```

### openSUSE

```bash
sudo zypper install python3-devel portaudio-devel python3-pipx
```

## Step 2: Ensure pipx is in PATH

After installing pipx, ensure it's in your PATH:

```bash
pipx ensurepath
source ~/.bashrc  # or restart your terminal
```

Verify pipx is working:

```bash
pipx --version
```

## Step 3: Clone the Repository

```bash
git clone https://github.com/Zebastjan/Syllablaze.git
cd Syllablaze
```

## Step 4: Install Syllablaze

Use the provided installation script:

```bash
python3 install.py
```

This will:
1. Install Syllablaze and dependencies in an isolated pipx environment
2. Create a desktop entry (`~/.local/share/applications/syllablaze.desktop`)
3. Make the `syllablaze` command available globally

**Installation location:** `~/.local/pipx/venvs/syllablaze/`

## Step 5: Verify Installation

Launch Syllablaze from your application menu or run:

```bash
syllablaze
```

You should see the Syllablaze icon appear in your system tray.

## First Run

On first launch:
1. Syllablaze will download the default Whisper model (`base`) - this takes a few minutes
2. Right-click the tray icon → Settings to configure
3. Test recording with the global shortcut (default: Alt+Space)

## Troubleshooting Installation

### pipx command not found

Ensure pipx is installed and in your PATH:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
source ~/.bashrc
```

### portaudio errors during installation

Install portaudio development headers:

```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev

# Fedora
sudo dnf install portaudio-devel

# Arch
sudo pacman -S portaudio
```

Then retry installation:

```bash
python3 install.py
```

### Installation succeeds but command not found

Verify pipx binary directory is in PATH:

```bash
echo $PATH | grep .local/bin
```

If not present, run:

```bash
pipx ensurepath
source ~/.bashrc
```

### Permission denied errors

Never use `sudo` with pipx. pipx installs user-level packages:

```bash
# WRONG
sudo python3 install.py

# CORRECT
python3 install.py
```

## Updating Syllablaze

To update to the latest version:

```bash
cd Syllablaze
git pull
python3 install.py  # Reinstalls with --force flag
```

## Uninstalling

To uninstall Syllablaze:

```bash
cd Syllablaze
python3 uninstall.py
```

This removes:
- The pipx installation
- Desktop entry
- Tray icon

**Settings are preserved** in `~/.config/Syllablaze/` - delete manually if desired.

## Next Steps

- **[Quick Start Guide](quick-start.md)** - Make your first recording
- **[Settings Reference](../user-guide/settings-reference.md)** - Configure Syllablaze
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

---

**Need help?** Check the [Troubleshooting Guide](troubleshooting.md) or [open an issue](https://github.com/Zebastjan/Syllablaze/issues).
