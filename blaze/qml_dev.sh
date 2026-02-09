#!/bin/bash
# QML/Kirigami Development Script for Syllablaze

set -e

echo "=== Syllablaze Kirigami Development Environment ==="
echo "KDE Plasma Version: $(plasmashell --version 2>/dev/null || echo 'Unknown')"
echo "Kirigami Available: $(pacman -Q kirigami 2>/dev/null && echo 'Yes' || echo 'No')"
echo

# Check if we're in the right directory
if [ ! -f "blaze/main.py" ]; then
    echo "Error: Run this script from the Syllablaze root directory"
    exit 1
fi

# Function to test Kirigami integration
test_kirigami() {
    echo "🧪 Testing Kirigami Integration..."
    
    # Test QML file syntax
    if [ -f "blaze/qml/test/TestWindow.qml" ]; then
        echo "✓ Test QML file exists"
    else
        echo "✗ Test QML file missing"
        return 1
    fi
    
    # Test Python-QML bridge
    if python3 -c "from blaze.kirigami_bridge import KirigamiBridge; print('✓ KirigamiBridge import successful')" 2>/dev/null; then
        echo "✓ KirigamiBridge import successful"
    else
        echo "✗ KirigamiBridge import failed"
        return 1
    fi
    
    # Test QML preview tool
    if python3 -c "from blaze.qml_preview import QMLPreview; print('✓ QMLPreview import successful')" 2>/dev/null; then
        echo "✓ QMLPreview import successful"
    else
        echo "✗ QMLPreview import failed"
        return 1
    fi
    
    echo "✅ Kirigami integration test passed"
    return 0
}

# Function to start QML preview
start_preview() {
    local qml_file="${1:-blaze/qml/test/TestWindow.qml}"
    
    if [ ! -f "$qml_file" ]; then
        echo "Error: QML file not found: $qml_file"
        return 1
    fi
    
    echo "🚀 Starting QML Preview: $qml_file"
    python3 blaze/qml_preview.py "$qml_file"
}

# Function to create development environment
setup_environment() {
    echo "🔧 Setting up Kirigami Development Environment..."
    
    # Create necessary directories
    mkdir -p blaze/qml/{components,common,pages,test}
    
    # Make scripts executable
    chmod +x blaze/qml_preview.py blaze/kirigami_bridge.py
    
    echo "✅ Development environment setup complete"
}

# Function to show available QML files
list_qml_files() {
    echo "📁 Available QML Files:"
    find blaze/qml -name "*.qml" -type f | while read file; do
        echo "  - $file"
    done
}

# Main menu
case "${1:-help}" in
    "test")
        test_kirigami
        ;;
    "preview")
        start_preview "$2"
        ;;
    "setup")
        setup_environment
        ;;
    "list")
        list_qml_files
        ;;
    "help"|"")
        echo "Usage: $0 [command]"
        echo "Commands:"
        echo "  test     - Test Kirigami integration"
        echo "  preview [file] - Start QML preview (default: test/TestWindow.qml)"
        echo "  setup    - Set up development environment"
        echo "  list     - List available QML files"
        echo "  help     - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac