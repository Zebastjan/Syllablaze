#!/bin/bash

# Script to update installed Syllablaze with current repository files
# This is for development purposes only

# Find the installed package directory
INSTALL_DIR=$(find ~/.local/share/pipx/venvs/syllablaze/lib/python* -type d -name "blaze" 2>/dev/null)

if [ -z "$INSTALL_DIR" ]; then
    echo "Error: Could not find installed Syllablaze package directory"
    exit 1
fi

echo "Found installed package at: $INSTALL_DIR"

# Copy all Python files from the repository to the installed location
echo "Copying Python files from repository to installed location..."
cp -v ./*.py "$INSTALL_DIR/"
cp -v ./blaze/*.py "$INSTALL_DIR/"
echo "Copied files from blaze/ directory"

# Make the script executable if it exists
if [ -f "./run-syllablaze.sh" ]; then
    echo "Updating run script..."
    cp -v ./run-syllablaze.sh "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/run-syllablaze.sh"
fi

echo "Update complete!"
echo "You can now run 'syllablaze' to use the updated version"

# Run the application by default
echo "Starting Syllablaze..."
syllablaze