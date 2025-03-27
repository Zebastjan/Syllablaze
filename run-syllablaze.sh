#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Set environment variables to suppress Jack errors
export JACK_NO_AUDIO_RESERVATION=1
export JACK_NO_START_SERVER=1
export DISABLE_JACK=1

# Run the application and filter out Jack-related error messages
python "$SCRIPT_DIR/main.py" 2> >(grep -v -E "jack server|Cannot connect to server|JackShmReadWritePtr")
