#!/bin/bash
# Setup script for the execute-code skill
# This script installs all dependencies needed to run the skill standalone

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${SKILL_DIR}/.venv"

echo "🔧 Setting up execute-code skill..."

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python 3.8+ is required. Found Python $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"

# Enable KVM support (required for Hyperlight)
# Note: This sets mode 0666 which allows any user to access KVM.
# For production systems, consider using group-based access control instead.
enable_kvm() {
    echo "🔧 Enabling KVM access..."
    if ! echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules; then
        echo "❌ Failed to create udev rule"
        return 1
    fi
    if ! sudo udevadm control --reload-rules; then
        echo "❌ Failed to reload udev rules"
        return 1
    fi
    if ! sudo udevadm trigger --name-match=kvm; then
        echo "❌ Failed to trigger udev"
        return 1
    fi
    if ! sudo chmod 666 /dev/kvm; then
        echo "❌ Failed to chmod /dev/kvm"
        return 1
    fi
    echo "✅ KVM access enabled"
    return 0
}

# Check for KVM support and enable if needed
if [ -e /dev/kvm ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    echo "✅ KVM is available and accessible"
elif [ -e /dev/kvm ]; then
    # KVM device exists but not accessible
    echo "⚠️  /dev/kvm exists but is not accessible"
    if command -v sudo &> /dev/null; then
        echo "🔧 Attempting to enable KVM access with sudo..."
        if enable_kvm; then
            echo "✅ KVM access enabled successfully"
        else
            echo "⚠️  Failed to enable KVM access. You may need to run manually:"
            echo "   sudo chmod 666 /dev/kvm"
        fi
    else
        echo "⚠️  sudo not available. Please enable KVM access manually:"
        echo "   sudo chmod 666 /dev/kvm"
    fi
else
    echo "⚠️  Warning: /dev/kvm not found. Hyperlight requires KVM support."
    echo "   The skill will still be installed, but code execution will fail without KVM."
    echo "   See: https://github.com/hyperlight-dev/hyperlight-nanvix#requirements"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Check for Rust/Cargo (required for building hyperlight-nanvix)
if ! command -v rustup &> /dev/null && [ ! -x "${CARGO_HOME:-$HOME/.cargo}/bin/rustup" ]; then
    echo "📦 Rust not found."
    echo "⚠️  This script will download and install Rust from https://rustup.rs"
    echo "   For manual installation, visit: https://www.rust-lang.org/tools/install"
    read -p "   Continue with automatic installation? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Rust is required. Please install Rust manually and re-run this script."
        exit 1
    fi
    echo "📦 Installing Rust from https://rustup.rs..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "${CARGO_HOME:-$HOME/.cargo}/env"
fi

# Install Rust nightly (required for hyperlight-nanvix)
# Note: hyperlight-nanvix may have a rust-toolchain.toml that pins the exact version
echo "🔧 Installing Rust nightly toolchain..."
"${CARGO_HOME:-$HOME/.cargo}/bin/rustup" install nightly

# Clone and build hyperlight-nanvix
VENDOR_DIR="${SKILL_DIR}/vendor"
HYPERLIGHT_DIR="${VENDOR_DIR}/hyperlight-nanvix"

if [ ! -d "$HYPERLIGHT_DIR" ]; then
    echo "📥 Cloning hyperlight-nanvix..."
    mkdir -p "$VENDOR_DIR"
    git clone https://github.com/hyperlight-dev/hyperlight-nanvix.git "$HYPERLIGHT_DIR"
else
    echo "📥 Updating hyperlight-nanvix..."
    cd "$HYPERLIGHT_DIR" && git pull
fi

# Install maturin and build hyperlight-nanvix
echo "🔧 Building hyperlight-nanvix Python bindings..."
pip install maturin

cd "$HYPERLIGHT_DIR"
if ! VIRTUAL_ENV="$VENV_DIR" maturin develop --features python; then
    echo ""
    echo "❌ Failed to build hyperlight-nanvix."
    echo "   Common issues:"
    echo "   - Missing Rust nightly toolchain: rustup install nightly"
    echo "   - Missing build dependencies: check hyperlight-nanvix README"
    echo "   - KVM not available: required for runtime, not build"
    echo ""
    echo "   For help, see: https://github.com/hyperlight-dev/hyperlight-nanvix"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use the skill, activate the virtual environment:"
echo "    source ${VENV_DIR}/bin/activate"
echo ""
echo "Then run:"
echo "    python3 ${SCRIPT_DIR}/run.py --lang javascript --code 'console.log(\"Hello!\");'"
echo "    python3 ${SCRIPT_DIR}/run.py --lang python --code 'print(\"Hello!\")'"
