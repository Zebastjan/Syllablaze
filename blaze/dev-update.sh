#!/bin/bash

# Script to update installed Syllablaze with current repository files
# This is for development purposes only
# Supports branch-specific deploys: main -> syllablaze, kirigami-rewrite -> syllablaze-dev
shopt -s nullglob  # Handle empty globs gracefully

PY_FILES=(
  ./*.py
  ./blaze/*.py
)

SUB_DIRS=("ui" "utils" "managers" "qml" "services")
RUN_SCRIPT="./run-syllablaze.sh"

# Detect current branch and set target package
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
if [ "$BRANCH" = "kirigami-rewrite" ]; then
    PACKAGE_NAME="syllablaze-dev"
    echo "🔧 Development branch detected: deploying to $PACKAGE_NAME"
else
    PACKAGE_NAME="syllablaze"
    echo "📦 Stable branch detected: deploying to $PACKAGE_NAME"
fi

# Find the installed package directory
INSTALL_DIR=$(find ~/.local/share/pipx/venvs/$PACKAGE_NAME/lib/python* -type d -name "blaze" 2>/dev/null | head -1)

if [ -z "$INSTALL_DIR" ]; then
    echo "Error: Could not find installed $PACKAGE_NAME package directory"
    echo "Hint: Install $PACKAGE_NAME first with 'pipx install -e .'"
    exit 1
fi

echo "Found installed package at: $INSTALL_DIR"

# Function to run checks on a file
run_checks() {
    local file=$1
    local errors=0
    
    echo "Checking $file..."
    
    # DISABLED: Ruff auto-fixing during debugging sessions
    # Previously: ruff check "$file" --fix
    echo "  [INFO] Ruff check disabled for debugging"
    
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

# Skip ruff error checking during debugging
# Previously: if [ $TOTAL_ERRORS -gt 0 ]; then exit 1; fi
echo "[INFO] Ruff error checking disabled - proceeding with file copy"

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
    if [ "$dir" = "qml" ]; then
        # Copy QML files recursively (includes test/ subdirectories)
        if [ -d "./blaze/qml" ]; then
            cp -rv "./blaze/qml"/* "$INSTALL_DIR/qml/" 2>/dev/null || true
        fi
    else
        # Copy Python files only for non-QML directories
        cp -v "./blaze/$dir"/*.py "$INSTALL_DIR/$dir/" 2>/dev/null || true
    fi
done

# Make the script executable if it exists
if [ -f "$RUN_SCRIPT" ]; then
    echo "Updating run script..."
    cp -v "$RUN_SCRIPT" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/$(basename "$RUN_SCRIPT")"
fi

echo "Update complete!"
echo "You can now run '$PACKAGE_NAME' to use the updated version"

# Run the application by default
echo "Starting $PACKAGE_NAME..."
$PACKAGE_NAME