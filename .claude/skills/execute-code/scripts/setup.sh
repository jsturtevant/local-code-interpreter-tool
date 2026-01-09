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

# Check for KVM support (required for Hyperlight)
if [ -e /dev/kvm ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    echo "✅ KVM is available and accessible"
elif [ -e /dev/kvm ]; then
    # KVM device exists but is not accessible
    echo "❌ Error: /dev/kvm exists but is not accessible."
    echo ""
    echo "   To enable KVM access, run one of the following options:"
    echo ""
    echo "   Option 1: For CI/servers (grants access to all users)"
    echo "     echo 'KERNEL==\"kvm\", GROUP=\"kvm\", MODE=\"0666\", OPTIONS+=\"static_node=kvm\"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules"
    echo "     sudo udevadm control --reload-rules"
    echo "     sudo udevadm trigger --name-match=kvm"
    echo "     sudo chmod 666 /dev/kvm"
    echo ""
    echo "   Option 2: For local development (add your user to the kvm group)"
    echo "     sudo usermod -aG kvm \$USER"
    echo "     # Then log out and back in for the group change to take effect"
    echo ""
    echo "   After enabling KVM access, re-run this setup script."
    exit 1
else
    echo "❌ Error: /dev/kvm not found. Hyperlight requires KVM support."
    echo ""
    echo "   KVM (Kernel-based Virtual Machine) is required for Hyperlight to run."
    echo "   Please ensure your system supports hardware virtualization and that"
    echo "   the KVM kernel module is loaded."
    echo ""
    echo "   For more information, see:"
    echo "     https://github.com/hyperlight-dev/hyperlight-nanvix#requirements"
    exit 1
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
