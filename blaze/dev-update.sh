#!/bin/bash

# Script to update installed Syllablaze with current repository files
# This is for development purposes only
shopt -s nullglob  # Handle empty globs gracefully

PY_FILES=(
  ./*.py
  ./blaze/*.py
)

SUB_DIRS=("ui" "utils" "managers")
RUN_SCRIPT="./run-syllablaze.sh"

# Find the installed package directory
INSTALL_DIR=$(find ~/.local/share/pipx/venvs/syllablaze/lib/python* -type d -name "blaze" 2>/dev/null)

if [ -z "$INSTALL_DIR" ]; then
    echo "Error: Could not find installed Syllablaze package directory"
    exit 1
fi

echo "Found installed package at: $INSTALL_DIR"

# Function to run checks on a file
run_checks() {
    local file=$1
    local errors=0
    
    echo "Checking $file..."
    
    # Inside run_checks()
    ruff check "$file" --fix
    local ruff_exit_code=$?
    if [ $ruff_exit_code -ne 0 ]; then
        echo "  [ERROR] Ruff check failed for $file (post-fix)"
        errors=$((errors+1))
    fi
    
    return $errors
}

# Run checks on all files
TOTAL_ERRORS=0
for pattern in "${PY_FILES[@]}"; do
    for file in $pattern; do
        if [ -f "$file" ]; then
            run_checks "$file"
            TOTAL_ERRORS=$((TOTAL_ERRORS + $?))
        fi
    done
done

for dir in "${SUB_DIRS[@]}"; do
    for file in "./blaze/$dir"/*.py; do
        if [ -f "$file" ]; then
            run_checks "$file"
            TOTAL_ERRORS=$((TOTAL_ERRORS + $?))
        fi
    done
done

# Only proceed if no ruff errors found
if [ $TOTAL_ERRORS -gt 0 ]; then
    echo "Found $TOTAL_ERRORS ruff errors - not copying files"
    exit 1
fi

# Copy all Python files from the repository to the installed location
echo "Copying Python files from repository to installed location..."
for pattern in "${PY_FILES[@]}"; do
    cp -v $pattern "$INSTALL_DIR/"
done


# Create subdirectories if they don't exist
for dir in "${SUB_DIRS[@]}"; do
    mkdir -p "$INSTALL_DIR/$dir"
done

# Copy files from subdirectories
for dir in "${SUB_DIRS[@]}"; do
    cp -v "./blaze/$dir"/*.py "$INSTALL_DIR/$dir/"
done

# Make the script executable if it exists
if [ -f "$RUN_SCRIPT" ]; then
    echo "Updating run script..."
    cp -v "$RUN_SCRIPT" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/$(basename "$RUN_SCRIPT")"
fi

echo "Update complete!"
echo "You can now run 'syllablaze' to use the updated version"

# Run the application by default
echo "Starting Syllablaze..."
syllablaze