#!/bin/bash
# install_llama_mtmd_cli.sh
#
# Automated installation script for llama-mtmd-cli binary
# (required for Qwen backend multimodal audio support)
#
# Usage: ./install_llama_mtmd_cli.sh [install_dir]
#   install_dir: Optional. Defaults to ~/.local/bin

set -euo pipefail

# Configuration
INSTALL_DIR="${1:-$HOME/.local/bin}"
REPO_URL="https://github.com/ggml-org/llama.cpp.git"
BUILD_DIR=""
CUDA_AVAILABLE=false

# Progress reporting (parseable by Python)
progress() {
    echo "PROGRESS:$1:$2"
}

# Error reporting and exit
error_exit() {
    echo "ERROR:$1" >&2
    exit "${2:-1}"
}

# Cleanup function (called on exit)
cleanup() {
    if [ -n "${BUILD_DIR}" ] && [ -d "${BUILD_DIR}" ]; then
        progress 98 "Cleaning up temporary build files..."
        rm -rf "${BUILD_DIR}"
    fi
}

# Register cleanup trap
trap cleanup EXIT

# Check for required build dependencies
check_dependencies() {
    progress 2 "Checking build dependencies..."

    # Essential tools
    if ! command -v git &>/dev/null; then
        error_exit "Git not installed. Install with: sudo pacman -S git"
    fi

    if ! command -v cmake &>/dev/null; then
        error_exit "CMake not installed. Install with: sudo pacman -S cmake"
    fi

    if ! command -v gcc &>/dev/null || ! command -v g++ &>/dev/null; then
        error_exit "Build tools not installed. Install with: sudo pacman -S base-devel"
    fi

    progress 5 "Required build tools found"

    # Optional: Check for CUDA
    if command -v nvcc &>/dev/null; then
        CUDA_AVAILABLE=true
        CUDA_VERSION=$(nvcc --version | grep -oP 'release \K[0-9.]+' || echo "unknown")
        progress 7 "CUDA detected: version ${CUDA_VERSION}"
    else
        CUDA_AVAILABLE=false
        progress 7 "CUDA not found, building CPU-only version"
    fi
}

# Clone llama.cpp repository
clone_repository() {
    progress 10 "Cloning llama.cpp repository..."

    BUILD_DIR=$(mktemp -d -t llama-cpp-build.XXXXXX)
    if [ ! -d "${BUILD_DIR}" ]; then
        error_exit "Failed to create temporary build directory"
    fi

    if ! git clone --depth 1 "${REPO_URL}" "${BUILD_DIR}/llama.cpp" 2>&1 | while read -r line; do
        echo "  $line"
    done; then
        error_exit "Failed to clone llama.cpp repository. Check network connection."
    fi

    progress 25 "Repository cloned successfully"
}

# Configure build with CMake
configure_build() {
    progress 30 "Configuring build with CMake..."

    cd "${BUILD_DIR}/llama.cpp" || error_exit "Failed to enter build directory"
    mkdir build || error_exit "Failed to create build subdirectory"
    cd build || error_exit "Failed to enter build subdirectory"

    local CMAKE_ARGS=(
        "-DLLAMA_BUILD_EXAMPLES=ON"
        "-DCMAKE_BUILD_TYPE=Release"
    )

    if [ "$CUDA_AVAILABLE" = true ]; then
        CMAKE_ARGS+=("-DGGML_CUDA=ON")
        progress 32 "Configuring with CUDA support..."
    else
        progress 32 "Configuring CPU-only build..."
    fi

    if ! cmake .. "${CMAKE_ARGS[@]}" 2>&1 | while read -r line; do
        echo "  $line"
    done; then
        error_exit "CMake configuration failed. Check build logs above."
    fi

    progress 38 "Build configuration complete"
}

# Compile llama-mtmd-cli binary
compile_binary() {
    progress 40 "Compiling llama-mtmd-cli (this takes 5-15 minutes)..."

    local CORES
    CORES=$(nproc)
    progress 42 "Using ${CORES} CPU cores for parallel compilation"

    # Track compilation progress
    local last_percent=40
    if ! cmake --build . --target llama-mtmd-cli -j"${CORES}" 2>&1 | while read -r line; do
        # Parse build progress from output like "[42/298] Building CXX object..."
        if [[ $line =~ \[([0-9]+)/([0-9]+)\] ]]; then
            local current=${BASH_REMATCH[1]}
            local total=${BASH_REMATCH[2]}
            # Map to 40-85% range
            local percent=$((40 + (current * 45 / total)))

            # Only report every 5% to avoid spam
            if [ $((percent - last_percent)) -ge 5 ]; then
                progress "$percent" "Compiling: $current/$total files"
                last_percent=$percent
            fi
        fi
        echo "  $line"
    done; then
        error_exit "Compilation failed. See logs above for details."
    fi

    progress 85 "Compilation complete"
}

# Install binary to target directory
install_binary() {
    progress 87 "Installing to ${INSTALL_DIR}..."

    # Create installation directory if needed
    mkdir -p "${INSTALL_DIR}" || error_exit "Failed to create ${INSTALL_DIR}"

    # Copy binary
    local BINARY_PATH="${BUILD_DIR}/llama.cpp/build/bin/llama-mtmd-cli"
    if [ ! -f "${BINARY_PATH}" ]; then
        error_exit "Binary not found at expected path: ${BINARY_PATH}"
    fi

    if ! cp "${BINARY_PATH}" "${INSTALL_DIR}/"; then
        error_exit "Failed to copy binary to ${INSTALL_DIR}"
    fi

    # Make executable
    chmod +x "${INSTALL_DIR}/llama-mtmd-cli" || error_exit "Failed to set executable permissions"

    progress 92 "Binary installed to ${INSTALL_DIR}/llama-mtmd-cli"
}

# Verify installation works
verify_installation() {
    progress 95 "Verifying installation..."

    local INSTALLED_BINARY="${INSTALL_DIR}/llama-mtmd-cli"

    # Test that binary is executable
    if [ ! -x "${INSTALLED_BINARY}" ]; then
        error_exit "Binary installed but not executable: ${INSTALLED_BINARY}"
    fi

    # Test that binary runs (check --help)
    if ! "${INSTALLED_BINARY}" --help >/dev/null 2>&1; then
        error_exit "Binary verification failed. Missing shared libraries? Try: ldd ${INSTALLED_BINARY}"
    fi

    progress 98 "Installation verified successfully"
}

# Main installation workflow
main() {
    progress 0 "Starting llama-mtmd-cli installation..."

    check_dependencies
    clone_repository
    configure_build
    compile_binary
    install_binary
    verify_installation

    progress 100 "Installation complete! Binary at: ${INSTALL_DIR}/llama-mtmd-cli"
}

# Run main workflow
main
