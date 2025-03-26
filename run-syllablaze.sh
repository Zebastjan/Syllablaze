#!/bin/bash
source /home/jones2/work/Syllablaze/venv/bin/activate

# Set environment variables to suppress Jack errors
export JACK_NO_AUDIO_RESERVATION=1
export JACK_NO_START_SERVER=1
export DISABLE_JACK=1

# Run the application and filter out Jack-related error messages
python /home/jones2/work/Syllablaze/main.py 2> >(grep -v -E "jack server|Cannot connect to server|JackShmReadWritePtr")
