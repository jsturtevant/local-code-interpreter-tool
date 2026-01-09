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
if [ ! -e /dev/kvm ]; then
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
    echo "📦 Rust not found. Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "${CARGO_HOME:-$HOME/.cargo}/env"
fi

# Install Rust nightly (required for hyperlight-nanvix)
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
cd "$HYPERLIGHT_DIR" && VIRTUAL_ENV="$VENV_DIR" maturin develop --features python

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use the skill, activate the virtual environment:"
echo "    source ${VENV_DIR}/bin/activate"
echo ""
echo "Then run:"
echo "    python3 ${SCRIPT_DIR}/run.py --lang javascript --code 'console.log(\"Hello!\");'"
echo "    python3 ${SCRIPT_DIR}/run.py --lang python --code 'print(\"Hello!\")'"
